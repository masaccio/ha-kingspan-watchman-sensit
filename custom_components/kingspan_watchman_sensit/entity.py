"""SENSiTEntity class"""
import logging

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME, VERSION

_LOGGER: logging.Logger = logging.getLogger(__package__)


class SENSiTEntity(CoordinatorEntity):
    def __init__(self, coordinator, config_entry):
        _LOGGER.debug("Init entity %s", self._attr_name)
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    def unique_id(self):
        _LOGGER.debug(f"unique_id: self={self.__dict__}")
        return None
        # return f"sensit-{self._tank_data.serial_number}-{self._sensor_name}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": NAME,
            "model": VERSION,
            "manufacturer": NAME,
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            "attribution": ATTRIBUTION,
            "id": str(self.coordinator.data.get("id")),
            "integration": DOMAIN,
        }

    @property
    def last_reset(self):
        """Time sensor was initialised (returns None)"""
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("SENSiTEntity._handle_coordinator_update")
        self._tank_data = self.coordinator.data
        self.async_write_ha_state()
