"""SENSiTEntity class"""

import logging
from functools import cached_property

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import TankData
from .const import ATTRIBUTION, DOMAIN, MANUFACTURER, MODEL
from .coordinator import SENSiTDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


class SENSiTEntity(CoordinatorEntity[SENSiTDataUpdateCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SENSiTDataUpdateCoordinator,
        config_entry: ConfigEntry,
        idx: int,
    ) -> None:
        _LOGGER.debug("Init entity %s", self._attr_name)
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.idx = idx

    @cached_property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        serial_no = self.coordinator.data[self.idx].serial_number
        name = (self._attr_name or "").lower().replace(" ", "_")
        return f"sensit-{serial_no}-{name}"

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.data[self.idx].serial_number)},
            model=MODEL,
            name=self.coordinator.data[self.idx].name,
            manufacturer=MANUFACTURER,
        )

    @cached_property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return {
            "attribution": ATTRIBUTION,
            "id": self.coordinator.data[self.idx].serial_number,
            "integration": DOMAIN,
        }

    @property
    def last_reset(self) -> None:
        """Time sensor was initialized (returns None)"""
        return None

    @property
    def available(self) -> bool:
        return super().available and self.idx < len(self.coordinator.data)
