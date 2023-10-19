"""Sensor platform for Kingspan Watchman SENSiT."""
import logging
from datetime import timedelta
from decimal import Decimal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, TIME_DAYS, UnitOfVolume
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
    _LOGGER.debug("Adding sensor entities")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for idx in range(len(coordinator.data)):
        entities += [
            OilLevel(coordinator, config_entry, idx),
            TankPercentageFull(coordinator, config_entry, idx),
            TankCapacity(coordinator, config_entry, idx),
            LastReadDate(coordinator, config_entry, idx),
            CurrentUsage(coordinator, config_entry, idx),
            ForcastEmpty(coordinator, config_entry, idx),
        ]
    async_add_entities(entities)


class OilLevel(SENSiTEntity, SensorEntity):
    _attr_icon = "mdi:gauge"
    _attr_name = "Oil Level"
    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        """Return the oil level in litres"""
        _LOGGER.debug(
            "Read oil level: %d litres", self.coordinator.data[self.idx].level
        )
        return self.coordinator.data[self.idx].level

    @property
    def icon(self):
        """Icon to use in the frontend"""
        return tank_icon(
            self.coordinator.data[self.idx].level,
            self.coordinator.data[self.idx].capacity,
        )


class TankPercentageFull(SENSiTEntity, SensorEntity):
    _attr_name = "Tank Percentage Full"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        """Return the oil level as a percentage"""
        percent_full = 100 * (
            self.coordinator.data[self.idx].level
            / self.coordinator.data[self.idx].capacity
        )
        _LOGGER.debug("Read oil level: %.1f percent", percent_full)
        return Decimal(f"{percent_full:.1f}")

    @property
    def icon(self):
        """Icon to use in the frontend"""
        return tank_icon(
            self.coordinator.data[self.idx].level,
            self.coordinator.data[self.idx].capacity,
        )


class TankCapacity(SENSiTEntity, SensorEntity):
    _attr_icon = "mdi:gauge-full"
    _attr_name = "Tank Capacity"
    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS

    @property
    def native_value(self):
        """Return the tank capacity in litres"""
        _LOGGER.debug(
            "Read tank capcity: %d litres",
            self.coordinator.data[self.idx].capacity,
        )
        return self.coordinator.data[self.idx].capacity


class LastReadDate(SENSiTEntity, SensorEntity):
    _attr_icon = "mdi:clock-outline"
    _attr_name = "Last Reading Date"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        """Return date of the last reading"""
        _LOGGER.debug(
            "Tank last read %s", str(self.coordinator.data[self.idx].last_read)
        )
        return self.coordinator.data[self.idx].last_read


class CurrentUsage(SENSiTEntity, SensorEntity):
    _attr_icon = "mdi:gauge-full"
    _attr_name = "Current Usage"
    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        """Return the usage in the last day in litres"""
        current_usage = self.coordinator.data[self.idx].usage_rate
        _LOGGER.debug("Current oil usage %d days", current_usage)
        return Decimal(f"{current_usage:.1f}")


class ForcastEmpty(SENSiTEntity, SensorEntity):
    _attr_icon = "mdi:calendar"
    _attr_name = "Forecast Empty"
    _attr_native_unit_of_measurement = TIME_DAYS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the number of days to empty"""
        empty_days = self.coordinator.data[self.idx].forecast_empty
        _LOGGER.debug("Tank forecast empty %d days", empty_days)
        return empty_days
        return timedelta(days=empty_days)


def tank_icon(level: int, capacity: int) -> str:
    percent_full = level / capacity
    if percent_full >= 0.75:
        return "mdi:gauge-full"
    elif percent_full >= 0.5:
        return "mdi:gauge"
    elif percent_full >= 0.25:
        return "mdi:gauge-low"
    else:
        return "mdi:gauge-empty"
