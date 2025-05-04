"""Test Kingspan Watchman SENSiT sensor states."""

import asyncio
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from connectsensor.exceptions import APIError
from custom_components.kingspan_watchman_sensit import async_unload_entry
from custom_components.kingspan_watchman_sensit.const import DOMAIN
from homeassistant.const import ATTR_ICON
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import UpdateFailed
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
    await hass.async_block_till_done()

    state = hass.states.get("sensor.oil_level")
    assert state
    assert state.state == str(MOCK_TANK_LEVEL)
    assert state.attributes.get(ATTR_ICON) == "mdi:gauge"

    state = hass.states.get("sensor.tank_capacity")
    assert state
    assert state.state == str(MOCK_TANK_CAPACITY)
    assert state.attributes.get(ATTR_ICON) == "mdi:gauge-full"

    state = hass.states.get("sensor.tank_percentage_full")
    assert state
    assert state.state == str(100 * (MOCK_TANK_LEVEL / MOCK_TANK_CAPACITY))
    assert state.attributes.get(ATTR_ICON) == "mdi:gauge"

    state = hass.states.get("sensor.current_usage")
    assert state.state == "96.7"
    assert state.attributes.get(ATTR_ICON) == "mdi:gauge-full"

    state = hass.states.get("sensor.forecast_empty")
    assert state.state == "10"
    assert state.attributes.get(ATTR_ICON) == "mdi:calendar"

    state = hass.states.get("sensor.oil_consumption")
    assert state.state == "12.1"
    assert state.attributes.get(ATTR_ICON) == "mdi:fire"

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

    state = hass.states.get("sensor.last_reading_date")
    assert state
    assert state.attributes.get(ATTR_ICON) == "mdi:clock-outline"
    assert state.state == reference_date

    assert await async_unload_entry(hass, config_entry)


async def test_sensor_with_timezone(hass, mock_sensor_client):
    await run_sensor_test_with_timezone(hass, "Asia/Kolkata")


async def test_sensor_with_utc(hass, mock_sensor_client):
    await run_sensor_test_with_timezone(hass, "UTC")


async def test_restore_sensor_state(hass, mock_sensor_client):
    """Test sensor saved state."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    mock_restore_cache(
        hass,
        [State("sensor.oil_consumption", "1234.5")],
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.oil_consumption")
    assert state.state == "1246.6"

    assert await async_unload_entry(hass, config_entry)


async def test_sensor_exceptions(hass, mock_sensor_client, mocker, caplog):
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    caplog.clear()
    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=asyncio.TimeoutError)
    with pytest.raises(UpdateFailed):
        await hass.data[DOMAIN][config_entry.entry_id].update()
    assert len(caplog.record_tuples) == 1
    assert "Timeout error fetching data" in caplog.record_tuples[0][2]

    caplog.clear()
    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=APIError("api-test error"))
    with pytest.raises(UpdateFailed):
        await hass.data[DOMAIN][config_entry.entry_id].update()
    assert len(caplog.record_tuples) == 1
    assert "API error fetching data for test@example.com" in caplog.record_tuples[0][2]

    caplog.clear()
    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=Exception())
    with pytest.raises(UpdateFailed):
        await hass.data[DOMAIN][config_entry.entry_id].update()
    assert len(caplog.record_tuples) == 1
    assert "Unhandled error" in caplog.record_tuples[0][2]


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


@pytest.mark.parametrize("mock_sensor_client", [[MOCK_TANK_CAPACITY]], indirect=True)
async def test_sensor_icon_full(hass, mock_sensor_client):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.oil_level")
    assert state
    assert state.state == str(MOCK_TANK_CAPACITY)
    assert state.attributes.get(ATTR_ICON) == "mdi:gauge-full"

    assert await async_unload_entry(hass, config_entry)


@pytest.mark.parametrize("mock_sensor_client", [[100]], indirect=True)
async def test_sensor_icon_empty(hass, mock_sensor_client):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.oil_level")
    assert state
    assert state.state == str(100)
    assert state.attributes.get(ATTR_ICON) == "mdi:gauge-empty"

    assert await async_unload_entry(hass, config_entry)


@pytest.mark.parametrize("mock_sensor_client", [[MOCK_TANK_CAPACITY * 0.3]], indirect=True)
async def test_sensor_icon_low(hass, mock_sensor_client):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.oil_level")
    assert state
    assert state.state == str(MOCK_TANK_CAPACITY * 0.3)
    assert state.attributes.get(ATTR_ICON) == "mdi:gauge-low"

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

    state = hass.states.get("sensor.current_usage")
    assert state
    assert state.state == "0.0"

    state = hass.states.get("sensor.forecast_empty")
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

    state = hass.states.get("sensor.current_usage")
    assert state
    assert state.state == "0.0"

    state = hass.states.get("sensor.forecast_empty")
    assert state
    assert state.state == "0"

    assert await async_unload_entry(hass, config_entry)
