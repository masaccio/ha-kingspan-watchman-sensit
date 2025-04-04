"""SENSiTEntity class"""

import logging
from functools import cached_property

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME

_LOGGER: logging.Logger = logging.getLogger(__package__)


class SENSiTEntity(CoordinatorEntity):
    def __init__(self, coordinator, config_entry, idx):
        _LOGGER.debug("Init entity %s", self._attr_name)
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.idx = idx

    @cached_property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        serial_no = self.coordinator.data[self.idx].serial_number
        name = self._attr_name.lower().replace(" ", "_")  # type: ignore
        return f"sensit-{serial_no}-{name}"

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.data[self.idx].serial_number)},
            model=self.coordinator.data[self.idx].model,
            name=self.coordinator.data[self.idx].name,
            manufacturer=NAME,
        )

    @cached_property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "attribution": ATTRIBUTION,
            "id": self.coordinator.data[self.idx].serial_number,
            "integration": DOMAIN,
        }

    @property
    def last_reset(self):
        """Time sensor was initialised (returns None)"""
        return None
