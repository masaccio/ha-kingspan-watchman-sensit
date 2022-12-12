"""Test Kingspan Watchman SENSiT sensor states."""
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.kingspan_watchman_sensit.const import DOMAIN
from custom_components.kingspan_watchman_sensit import async_unload_entry

from .const import MOCK_TANK_LEVEL, MOCK_TANK_CAPACITY, MOCK_TANK_LAST_READ
from homeassistant.const import ATTR_ICON


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
    assert state.state == MOCK_TANK_LAST_READ.isoformat()
    assert state.attributes.get(ATTR_ICON) == "mdi:clock-outline"

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
