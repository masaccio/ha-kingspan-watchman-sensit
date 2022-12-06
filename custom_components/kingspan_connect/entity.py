"""KingspanConnectEntity class"""
from homeassistant.const import UnitOfVolume
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.switch import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)

from .const import DOMAIN, NAME, VERSION, ATTRIBUTION


class KingspanConnectEntity(CoordinatorEntity):
    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self.config_entry.entry_id

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": NAME,
            "model": VERSION,
            "manufacturer": NAME,
        }

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "attribution": ATTRIBUTION,
            "id": str(self.coordinator.data.get("id")),
            "integration": DOMAIN,
        }


class OilLevel(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: CoordinatorEntity):
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        super().__init__(coordinator)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._level = self.coordinator.data.level
        self._tank_id = self.coordinator.data.serial_number
        self.async_write_ha_state()

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Oil Level"

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        tank_id = self._tank_id.lower()
        return f"sensit_{tank_id}_oil_level"

    @property
    def native_value(self):
        """Rteurn the oil level in native units"""
        return self._level

    @property
    def icon(self):
        """Icon to use in the frontend"""
        return "mdi:gauge"

    @property
    def last_reset(self):
        """Time sensor was initialised (returns None)"""
        return None


class LastReadingDate(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: CoordinatorEntity):
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        super().__init__(coordinator)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._last_read = self.coordinator.data.last_read
        self._tank_id = self.coordinator.data.serial_number
        self.async_write_ha_state()

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Last Read Date"

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        tank_id = self._tank_id.lower()
        return f"sensit_{tank_id}_last_read"

    @property
    def native_value(self):
        """Rteurn the last reading date"""
        return self._last_read

    @property
    def icon(self):
        """Icon to use in the frontend"""
        return "mdi:calendar-clock"

    @property
    def last_reset(self):
        """Time sensor was initialised (returns None)"""
        return None


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add sensors for passed config_entry in HA."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities([OilLevel(coordinator), LastReadingDate(coordinator)])
