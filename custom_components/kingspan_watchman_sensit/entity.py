"""SENSiTEntity class"""
import logging

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME

_LOGGER: logging.Logger = logging.getLogger(__package__)


class SENSiTEntity(CoordinatorEntity):
    def __init__(self, coordinator, config_entry):
        _LOGGER.debug("Init entity %s", self._attr_name)
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        serial_no = self.coordinator.data.serial_number
        name = self._attr_name.lower().replace(" ", "_")
        return f"sensit-{serial_no}-{name}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.data.serial_number)},
            "name": NAME,
            "model": self.coordinator.data.name,
            "manufacturer": NAME,
        }

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "attribution": ATTRIBUTION,
            "id": self.coordinator.data.serial_number,
            "integration": DOMAIN,
        }

    @property
    def last_reset(self):
        """Time sensor was initialised (returns None)"""
        return None
