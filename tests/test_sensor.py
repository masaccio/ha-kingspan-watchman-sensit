"""Test Kingspan Watchman SENSiT sensor states."""

import asyncio
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from connectsensor.exceptions import KingspanAPIError
from custom_components.kingspan_watchman_sensit import async_unload_entry
from custom_components.kingspan_watchman_sensit.api import (
    SENSiTApiClientError,
    SENSiTConnectionError,
)
from custom_components.kingspan_watchman_sensit.const import DEFAULT_OIL_ENERGY_DENSITY, DOMAIN
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from homeassistant.util.dt import get_time_zone, set_default_time_zone
from pytest_homeassistant_custom_component.common import MockConfigEntry, State, mock_restore_cache

from .const import (
    MOCK_CONFIG,
    MOCK_GET_DATA_METHOD,
    MOCK_TANK_CAPACITY,
    MOCK_TANK_LEVEL,
    MOCK_TANK_NAME,
    HistoryType,
)


async def test_sensor(hass, mock_sensor_client):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.tanky_mctankface_oil_level")
    assert state
    assert float(state.state) == float(MOCK_TANK_LEVEL)

    state = hass.states.get("sensor.tanky_mctankface_tank_capacity")
    assert state
    assert float(state.state) == float(MOCK_TANK_CAPACITY)

    state = hass.states.get("sensor.tanky_mctankface_tank_percentage_full")
    assert state
    assert float(state.state) == float(100 * (MOCK_TANK_LEVEL / MOCK_TANK_CAPACITY))

    state = hass.states.get("sensor.tanky_mctankface_current_usage")
    assert state.state == "96.7"

    state = hass.states.get("sensor.tanky_mctankface_forecast_empty")
    assert state.state == "10"

    assert await async_unload_entry(hass, config_entry)


async def run_sensor_test_with_timezone(hass, tz: str):
    """Test sensor timezone compliance."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    set_default_time_zone(get_time_zone(tz))  # type: ignore

    reference_date = (
        datetime.now(ZoneInfo(tz))
        .replace(hour=0, minute=30, second=0, microsecond=0)
        .astimezone(UTC)
        .isoformat()
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.tanky_mctankface_last_reading_date")
    assert state
    assert state.state == reference_date

    assert await async_unload_entry(hass, config_entry)


async def test_sensor_with_timezone(hass, mock_sensor_client):
    await run_sensor_test_with_timezone(hass, "Asia/Kolkata")


async def test_sensor_with_utc(hass, mock_sensor_client):
    await run_sensor_test_with_timezone(hass, "UTC")


async def test_current_energy_usage(hass, mock_sensor_client):
    """Test current energy usage sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_registry.async_update_entity(
        "sensor.tanky_mctankface_current_energy_usage",
        disabled_by=None,
    )
    await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.tanky_mctankface_current_energy_usage")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert state is not None
    assert state.state == str(round(coordinator.data[0].usage_rate * DEFAULT_OIL_ENERGY_DENSITY, 1))

    assert await async_unload_entry(hass, config_entry)


async def test_oil_consumption(hass, mock_sensor_client):
    """Test oil consumption read too early."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_registry.async_update_entity(
        "sensor.tanky_mctankface_oil_consumption",
        disabled_by=None,
    )
    await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.tanky_mctankface_oil_consumption")
    assert state is not None
    assert state.state == "unknown"

    assert await async_unload_entry(hass, config_entry)


async def test_oil_consumption_restore(hass, mock_sensor_client):
    """Test sensor saved state."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)

    consumption_total = 20000.0
    restore_state = State(
        "sensor.tanky_mctankface_oil_consumption",
        str(consumption_total),
        {
            "consumption_total": str(consumption_total),
            "consumption_last_read": str(dt_util.utcnow() - timedelta(hours=24)),
        },
    )
    mock_restore_cache(hass, [restore_state])

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_registry.async_update_entity(
        "sensor.tanky_mctankface_oil_consumption",
        disabled_by=None,
    )
    await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.tanky_mctankface_current_usage")
    consumption_total += round(float(state.state) * DEFAULT_OIL_ENERGY_DENSITY, 1)
    state = hass.states.get("sensor.tanky_mctankface_oil_consumption")
    assert state is not None
    assert state.state == str(consumption_total)

    assert await async_unload_entry(hass, config_entry)


async def test_sensor_exceptions(hass, mock_sensor_client, mocker):
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=asyncio.TimeoutError)
    with pytest.raises(SENSiTConnectionError) as exc:
        await hass.data[DOMAIN][config_entry.entry_id].update()
    assert str(exc.value) == "Timeout or connection error fetching data for test@example.com"

    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=KingspanAPIError("api-test error"))
    with pytest.raises(SENSiTApiClientError) as exc:
        await hass.data[DOMAIN][config_entry.entry_id].update()
    assert str(exc.value) == "API error fetching data for test@example.com: api-test error"

    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=Exception())
    with pytest.raises(SENSiTApiClientError):
        await hass.data[DOMAIN][config_entry.entry_id].update()
    assert str(exc.value) == "API error fetching data for test@example.com: api-test error"


@pytest.mark.parametrize(
    "mock_sensor_client", [[MOCK_TANK_LEVEL, HistoryType.DECREASING, 2]], indirect=True
)
async def test_sensor_multiple_tanks(hass, mock_sensor_client):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    device_entries = dr.async_get(hass).devices.values()
    assert list(device_entries)[0].name == MOCK_TANK_NAME + " #1"
    assert list(device_entries)[1].name == MOCK_TANK_NAME + " #2"

    assert await async_unload_entry(hass, config_entry)


@pytest.mark.parametrize(
    "mock_sensor_client", [[MOCK_TANK_CAPACITY, HistoryType.NONE]], indirect=True
)
async def test_sensor_no_history(hass, mock_sensor_client, caplog):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    caplog.clear()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    history_log = [x[2] for x in caplog.record_tuples if "No history" in x[2]]
    assert len(history_log) == 1

    state = hass.states.get("sensor.tanky_mctankface_current_usage")
    assert state
    assert state.state == "0.0"

    state = hass.states.get("sensor.tanky_mctankface_forecast_empty")
    assert state
    assert state.state == "0"

    assert await async_unload_entry(hass, config_entry)


@pytest.mark.parametrize(
    "mock_sensor_client", [[MOCK_TANK_CAPACITY, HistoryType.EXPIRED]], indirect=True
)
async def test_sensor_expired_history(hass, mock_sensor_client, caplog):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    caplog.clear()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.tanky_mctankface_current_usage")
    assert state
    assert state.state == "0.0"

    state = hass.states.get("sensor.tanky_mctankface_forecast_empty")
    assert state
    assert state.state == "0"

    assert await async_unload_entry(hass, config_entry)
