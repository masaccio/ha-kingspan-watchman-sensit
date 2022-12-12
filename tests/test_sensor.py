"""Test Kingspan Watchman SENSiT sensor states."""
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.kingspan_watchman_sensit.const import DOMAIN

from .const import MOCK_TANK_LEVEL, MOCK_TANK_CAPACITY, MOCK_TANK_LAST_READ
from homeassistant.const import (
    # ATTR_DEVICE_CLASS,
    ATTR_ICON,
    # ATTR_UNIT_OF_MEASUREMENT,
    # STATE_UNAVAILABLE,
)


@pytest.mark.asyncio
async def test_sensor(hass, mock_sensor_client):
    """Test sensor."""
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "simple config"})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
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

    # state = hass.states.get("sensor.last_reading_date")
    # assert state
    # assert state.state == str(MOCK_TANK_LAST_READ)
    # assert state.attributes.get(ATTR_ICON) == "mdi:clock-outline"
