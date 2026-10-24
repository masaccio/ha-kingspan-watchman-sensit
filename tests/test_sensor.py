"""Test Kingspan Watchman SENSiT sensor states."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from connectsensor.exceptions import KingspanAPIError
from custom_components.kingspan_watchman_sensit import async_unload_entry
from custom_components.kingspan_watchman_sensit.api import TankData
from custom_components.kingspan_watchman_sensit.const import DEFAULT_OIL_ENERGY_DENSITY, DOMAIN
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.dt import get_time_zone, set_default_time_zone
from pytest_homeassistant_custom_component.common import MockConfigEntry, State, mock_restore_cache

from .const import (
    MOCK_CONFIG,
    MOCK_GET_DATA_METHOD,
    MOCK_TANK_CAPACITY,
    MOCK_TANK_LEVEL,
    MOCK_TANK_NAME,
    MOCK_TANK_SERIAL_NUMBER,
    HistoryType,
)


async def test_sensor(hass, mock_sensor_client):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    coordinator = config_entry.runtime_data
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
    coordinator = config_entry.runtime_data
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


async def test_oil_consumption_restore(hass, mock_sensor_client, mocker):
    """Test sensor saved state and cumulative update processing."""
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

    # Mock a new API response to simulate a data update with a new reading date
    coordinator = config_entry.runtime_data
    new_tank_data = TankData(
        level=800.0,
        capacity=MOCK_TANK_CAPACITY,
        name=MOCK_TANK_NAME,
        serial_number=MOCK_TANK_SERIAL_NUMBER,
        last_read=dt_util.utcnow(),
        usage_rate=5.0,
    )

    mocker.patch.object(
        coordinator.api, "async_get_data", new_callable=AsyncMock, return_value=[new_tank_data]
    )

    # Verify the sensor processed the update and correctly added the new usage
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    expected_new_total = round(consumption_total + (5.0 * DEFAULT_OIL_ENERGY_DENSITY), 1)
    state = hass.states.get("sensor.tanky_mctankface_oil_consumption")
    assert state.state == str(expected_new_total)

    # Trigger a refresh with the SAME data to test totals are not re-computed
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    state = hass.states.get("sensor.tanky_mctankface_oil_consumption")
    assert state.state == str(expected_new_total)
    assert await async_unload_entry(hass, config_entry)


async def test_sensor_exceptions(hass, mock_sensor_client, mocker):
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data
    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=asyncio.TimeoutError)
    with pytest.raises(UpdateFailed) as exc:
        await coordinator._async_update_data()
    assert exc.value.translation_key == "timed_out"
    assert str(exc.value) == "Timed out while connecting to the Kingspan service"

    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=KingspanAPIError("api-test error"))
    with pytest.raises(UpdateFailed) as exc:
        await coordinator._async_update_data()
    assert str(exc.value).endswith("api-test error")


@pytest.mark.parametrize(
    "mock_sensor_client",
    [{"tank_level": MOCK_TANK_CAPACITY, "history_type": HistoryType.DECREASING, "num_tanks": 2}],
    indirect=True,
)
async def test_sensor_multiple_tanks(hass, mock_sensor_client):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    device_entries = dr.async_entries_for_config_entry(device_registry, config_entry.entry_id)

    assert device_entries[0].name == MOCK_TANK_NAME + " #1"
    assert device_entries[1].name == MOCK_TANK_NAME + " #2"
    assert await async_unload_entry(hass, config_entry)


@pytest.mark.parametrize(
    "mock_sensor_client",
    [{"tank_level": MOCK_TANK_CAPACITY, "history_type": HistoryType.NONE}],
    indirect=True,
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
    "mock_sensor_client",
    [{"tank_level": MOCK_TANK_CAPACITY, "history_type": HistoryType.EXPIRED}],
    indirect=True,
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
