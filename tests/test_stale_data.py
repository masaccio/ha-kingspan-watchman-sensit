"""Keep known readings during outages without treating them as fresh data."""

import asyncio
from dataclasses import asdict, replace
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from custom_components.kingspan_watchman_sensit.api import (
    SENSiTApiClient,
    SENSiTApiClientError,
    SENSiTAuthError,
    SENSiTConnectionError,
    SENSiTNoDataError,
)
from custom_components.kingspan_watchman_sensit.const import CONF_USERNAME, DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import State
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache

from .conftest import MockAsyncTank
from .const import MOCK_CONFIG, MOCK_TANK_LEVEL

OIL_LEVEL = "sensor.tanky_mctankface_oil_level"
OIL_CONSUMPTION = "sensor.tanky_mctankface_oil_consumption"


@pytest_asyncio.fixture
async def loaded_entry(hass, mock_sensor_client):
    """Set up a real entry with a successful initial API refresh."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    return entry


@pytest.mark.parametrize("error", [SENSiTConnectionError, SENSiTApiClientError])
async def test_outage_keeps_readings_and_recovery_clears_stale(hass, loaded_entry, mocker, error):
    """A failed refresh preserves values and timestamps until a successful response."""
    coordinator = loaded_entry.runtime_data
    previous_data = coordinator.data
    successful_at = coordinator.last_successful_update
    previous_state = hass.states.get(OIL_LEVEL)
    fetch = mocker.patch.object(
        coordinator.api, "async_get_data", AsyncMock(side_effect=error("offline"))
    )

    for _ in range(2):
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        state = hass.states.get(OIL_LEVEL)
        assert state.state == previous_state.state
        assert state.attributes["data_stale"] is True
        assert (
            state.attributes["last_successful_update"]
            == previous_state.attributes["last_successful_update"]
        )
        assert coordinator.data == previous_data
        assert coordinator.last_successful_update == successful_at

    new_data = [replace(previous_data[0], level=900.0)]
    fetch.side_effect = None
    fetch.return_value = new_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(OIL_LEVEL)
    assert float(state.state) == 900.0
    assert state.attributes["data_stale"] is False
    assert coordinator.last_successful_update >= successful_at


async def test_reload_offline_restores_snapshot_without_adding_consumption(
    hass, loaded_entry, hass_storage, mocker
):
    """Persisted readings survive a new coordinator without inventing consumption."""
    previous = loaded_entry.runtime_data
    successful_at = previous.last_successful_update
    snapshot = asdict(previous.data[0])
    snapshot.pop("history")
    stored = hass_storage[f"{DOMAIN}.{loaded_entry.entry_id}"]["data"]
    assert isinstance(stored["last_successful_update"], str)
    assert "password" not in stored

    mock_restore_cache(
        hass,
        [
            State(
                OIL_CONSUMPTION,
                "200.0",
                {
                    "consumption_total": 200.0,
                    "consumption_last_read": (
                        previous.data[0].last_read - timedelta(days=1)
                    ).isoformat(),
                },
            )
        ],
    )
    er.async_get(hass).async_update_entity(OIL_CONSUMPTION, disabled_by=None)
    mocker.patch.object(
        SENSiTApiClient, "async_get_data", AsyncMock(side_effect=SENSiTConnectionError("offline"))
    )

    await hass.config_entries.async_reload(loaded_entry.entry_id)
    await hass.async_block_till_done()

    restored = loaded_entry.runtime_data
    assert restored is not previous
    assert loaded_entry.state == ConfigEntryState.LOADED
    restored_snapshot = asdict(restored.data[0])
    restored_snapshot.pop("history")
    assert restored_snapshot == snapshot
    assert restored.last_successful_update == successful_at
    state = hass.states.get(OIL_LEVEL)
    assert float(state.state) == MOCK_TANK_LEVEL
    assert state.attributes["data_stale"] is True
    assert hass.states.get(OIL_CONSUMPTION).state == "200.0"


async def test_cold_start_offline_retries_without_fabricating_data(hass, mocker):
    """An installation with no saved readings still requests setup retry."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    entry.add_to_hass(hass)
    mocker.patch.object(
        SENSiTApiClient, "async_get_data", AsyncMock(side_effect=SENSiTConnectionError("offline"))
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.SETUP_RETRY
    assert hass.states.get(OIL_LEVEL) is None


async def test_cache_is_not_reused_for_another_account(hass, loaded_entry, mocker):
    """Changing credentials to a different account cannot expose the old tank."""
    await hass.config_entries.async_unload(loaded_entry.entry_id)
    hass.config_entries.async_update_entry(
        loaded_entry, data={**MOCK_CONFIG, CONF_USERNAME: "another@example.com"}
    )
    mocker.patch.object(
        SENSiTApiClient, "async_get_data", AsyncMock(side_effect=SENSiTConnectionError("offline"))
    )

    await hass.config_entries.async_setup(loaded_entry.entry_id)
    await hass.async_block_till_done()

    assert loaded_entry.state == ConfigEntryState.SETUP_RETRY
    assert hass.states.get(OIL_LEVEL).state == "unavailable"


@pytest.mark.parametrize("corrupt_field", ["last_successful_update", "level"])
async def test_corrupt_cache_is_ignored(hass, loaded_entry, hass_storage, mocker, corrupt_field):
    """Invalid saved readings must not prevent normal connection retry."""
    cached = hass_storage[f"{DOMAIN}.{loaded_entry.entry_id}"]["data"]
    if corrupt_field == "last_successful_update":
        cached[corrupt_field] = "not-a-timestamp"
    else:
        cached["tanks"][0][corrupt_field] = "not-a-number"
    mocker.patch.object(
        SENSiTApiClient, "async_get_data", AsyncMock(side_effect=SENSiTConnectionError("offline"))
    )

    await hass.config_entries.async_reload(loaded_entry.entry_id)
    await hass.async_block_till_done()

    assert loaded_entry.state == ConfigEntryState.SETUP_RETRY
    assert hass.states.get(OIL_LEVEL).state == "unavailable"


async def test_removing_entry_deletes_saved_readings(hass, loaded_entry, hass_storage):
    """Removing an account also removes its persisted tank snapshot."""
    storage_key = f"{DOMAIN}.{loaded_entry.entry_id}"
    assert storage_key in hass_storage

    await hass.config_entries.async_remove(loaded_entry.entry_id)
    await hass.async_block_till_done()

    assert storage_key not in hass_storage


@pytest.mark.parametrize("no_data", [[], SENSiTNoDataError("no level data")])
async def test_no_data_clears_cached_tanks(hass, loaded_entry, mocker, no_data):
    """An authoritative empty response cannot resurrect a removed tank later."""
    fetch = mocker.patch.object(SENSiTApiClient, "async_get_data", AsyncMock())
    if isinstance(no_data, Exception):
        fetch.side_effect = no_data
    else:
        fetch.return_value = no_data
    await loaded_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert loaded_entry.runtime_data.data == []

    fetch.side_effect = SENSiTConnectionError("offline")
    await hass.config_entries.async_reload(loaded_entry.entry_id)
    await hass.async_block_till_done()

    assert loaded_entry.state == ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (SENSiTAuthError("invalid credentials"), ConfigEntryAuthFailed),
        (asyncio.CancelledError(), asyncio.CancelledError),
    ],
)
async def test_cache_does_not_hide_auth_errors_or_cancellation(
    loaded_entry, mocker, error, expected
):
    """Reauthentication and Home Assistant shutdown retain their normal behavior."""
    coordinator = loaded_entry.runtime_data
    mocker.patch.object(coordinator.api, "async_get_data", AsyncMock(side_effect=error))

    with pytest.raises(expected):
        await coordinator._async_update_data()


async def test_blocked_history_times_out_and_keeps_last_reading(hass, loaded_entry, mocker):
    """Exercise the real API deadline rather than injecting a timeout exception."""
    cancelled = asyncio.Event()

    async def blocked_history(_tank):
        try:
            await asyncio.Future()
        finally:
            cancelled.set()

    mocker.patch.object(MockAsyncTank, "history", blocked_history)
    mocker.patch("custom_components.kingspan_watchman_sensit.api.API_TIMEOUT", 0.01)

    await asyncio.wait_for(loaded_entry.runtime_data.async_refresh(), timeout=1)
    await hass.async_block_till_done()

    assert cancelled.is_set()
    state = hass.states.get(OIL_LEVEL)
    assert float(state.state) == MOCK_TANK_LEVEL
    assert state.attributes["data_stale"] is True
