"""Sensor platform for Watchman SENSiT."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import SENSiTEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [OilLevel(coordinator, config_entry), TankCapacity(coordinator, config_entry)]
    )


class OilLevel(SENSiTEntity):
    _attr_icon = "mdi:gauge"
    _attr_name = "Oil Level"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS

    @property
    def native_value(self):
        """Return the oil level in litres"""
        _LOGGER.debug("OilLevel.native_value()")
        return self._tank_data.level

    @property
    def icon(self):
        """Icon to use in the frontend"""
        return "mdi:gauge"


class TankCapacity(SENSiTEntity):
    _attr_icon = "mdi:gauge"
    _attr_name = "Oil Level"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS

    @property
    def native_value(self):
        """Return thetank capacity in litres"""
        _LOGGER.debug("TankCapacity.native_value()")
        return self._tank_data.capacity
