"""Test Kingspan Watchman SENSiT sensor states."""
from datetime import datetime, timezone

import pytest
from homeassistant.const import ATTR_ICON
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kingspan_watchman_sensit import async_unload_entry
from custom_components.kingspan_watchman_sensit.const import DOMAIN

from .const import MOCK_TANK_CAPACITY, MOCK_TANK_LEVEL, HistoryType


@pytest.mark.asyncio
async def test_sensor(hass, mock_sensor_client):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "simple config"})

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

    state = hass.states.get("sensor.last_reading_date")
    assert state
    test_date = (
        datetime.now()
        .replace(hour=0, minute=30, second=0, microsecond=0)
        .replace(tzinfo=timezone.utc)
    )
    assert state.state == test_date.isoformat()
    assert state.attributes.get(ATTR_ICON) == "mdi:clock-outline"

    state = hass.states.get("sensor.current_usage")
    assert state.state == "80.0"
    assert state.attributes.get(ATTR_ICON) == "mdi:gauge-full"

    state = hass.states.get("sensor.forecast_empty")
    assert state.state == "15"
    assert state.attributes.get(ATTR_ICON) == "mdi:calendar"

    assert await async_unload_entry(hass, config_entry)


@pytest.mark.asyncio
@pytest.mark.parametrize("mock_sensor_client", [[MOCK_TANK_CAPACITY]], indirect=True)
async def test_sensor_icon_full(hass, mock_sensor_client):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "simple config"})

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.oil_level")
    assert state
    assert state.state == str(MOCK_TANK_CAPACITY)
    assert state.attributes.get(ATTR_ICON) == "mdi:gauge-full"

    assert await async_unload_entry(hass, config_entry)


@pytest.mark.asyncio
@pytest.mark.parametrize("mock_sensor_client", [[100]], indirect=True)
async def test_sensor_icon_empty(hass, mock_sensor_client):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "simple config"})

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.oil_level")
    assert state
    assert state.state == str(100)
    assert state.attributes.get(ATTR_ICON) == "mdi:gauge-empty"

    assert await async_unload_entry(hass, config_entry)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_sensor_client", [[MOCK_TANK_CAPACITY * 0.3]], indirect=True
)
async def test_sensor_icon_low(hass, mock_sensor_client):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "simple config"})

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.oil_level")
    assert state
    assert state.state == str(MOCK_TANK_CAPACITY * 0.3)
    assert state.attributes.get(ATTR_ICON) == "mdi:gauge-low"

    assert await async_unload_entry(hass, config_entry)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_sensor_client", [[MOCK_TANK_CAPACITY, HistoryType.NONE]], indirect=True
)
async def test_sensor_no_history(hass, mock_sensor_client, caplog):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "simple config"})

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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_sensor_client", [[MOCK_TANK_CAPACITY, HistoryType.EXPIRED]], indirect=True
)
async def test_sensor_expired_history(hass, mock_sensor_client, caplog):
    """Test sensor."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "simple config"})

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
