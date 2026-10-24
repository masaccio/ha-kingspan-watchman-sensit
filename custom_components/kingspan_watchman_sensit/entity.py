"""SENSiTEntity class"""

import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import TankData
from .const import ATTRIBUTION, CONF_NAME, DEFAULT_TANK_NAME, DOMAIN, MANUFACTURER, MODEL
from .coordinator import SENSiTConfigEntry, SENSiTDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


class SENSiTEntity(CoordinatorEntity[SENSiTDataUpdateCoordinator]):
    """Common entity behavior for Kingspan Watchman SENSiT sensors."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: SENSiTDataUpdateCoordinator,
        config_entry: SENSiTConfigEntry,
        serial_number: str,
        entity_description: EntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.config_entry = config_entry
        self.serial_number = serial_number

        tank = self.tank_data
        tank_name = (
            tank.name
            if tank.name and tank.name != "Unknown"
            else config_entry.data.get(CONF_NAME) or config_entry.title or DEFAULT_TANK_NAME
        )
        self._attr_unique_id = f"sensit-{self.serial_number}-{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.serial_number)},
            serial_number=self.serial_number,
            model=MODEL,
            name=tank_name,
            manufacturer=MANUFACTURER,
        )
        self._attr_extra_state_attributes = {
            "attribution": ATTRIBUTION,
            "id": self.serial_number,
            "integration": DOMAIN,
        }

    @property
    def tank_data(self) -> TankData:
        """Dynamically fetch data by serial number."""
        for tank in self.coordinator.data:  # pragma: no branch
            if tank.serial_number == self.serial_number:
                return tank
        # Should never be reached, defaults to zero values
        return TankData(serial_number=self.serial_number)  # pragma: no cover

    @property
    def last_reset(self) -> None:
        """Time sensor was initialized (returns None)"""
        return None

    @property
    def available(self) -> bool:
        return super().available and any(
            tank.serial_number == self.serial_number for tank in self.coordinator.data
        )
