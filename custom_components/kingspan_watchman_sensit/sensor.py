"""Sensor platform for Kingspan Watchman SENSiT."""

import logging
from datetime import timedelta
from decimal import Decimal
from functools import cached_property

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

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
    entities: list[SensorEntity] = []
    for idx in range(len(coordinator.data)):
        entities += [
            OilLevel(coordinator, config_entry, idx),
            TankPercentageFull(coordinator, config_entry, idx),
            TankCapacity(coordinator, config_entry, idx),
            LastReadDate(coordinator, config_entry, idx),
            CurrentUsage(coordinator, config_entry, idx),
            ForcastEmpty(coordinator, config_entry, idx),
            OilConsumption(coordinator, config_entry, idx),
        ]
    async_add_entities(entities)


class OilLevel(SENSiTEntity, SensorEntity):
    _attr_icon = "mdi:gauge"
    _attr_name = "Oil Level"
    _attr_device_class = SensorDeviceClass.VOLUME_STORAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS

    @cached_property
    def native_value(self):
        """Return the oil level in litres"""
        _LOGGER.debug("Read oil level: %d litres", self.coordinator.data[self.idx].level)
        return self.coordinator.data[self.idx].level

    @cached_property
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

    @cached_property
    def native_value(self):
        """Return the oil level as a percentage"""
        percent_full = 100 * (
            self.coordinator.data[self.idx].level / self.coordinator.data[self.idx].capacity
        )
        _LOGGER.debug("Read oil level: %.1f percent", percent_full)
        return Decimal(f"{percent_full:.1f}")

    @cached_property
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
    _attr_state_class = SensorStateClass.TOTAL

    @cached_property
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

    @cached_property
    def native_value(self):
        """Return date of the last reading"""
        _LOGGER.debug("Tank last read %s", str(self.coordinator.data[self.idx].last_read))
        return self.coordinator.data[self.idx].last_read


class CurrentUsage(SENSiTEntity, SensorEntity):
    _attr_icon = "mdi:gauge-full"
    _attr_name = "Current Usage"
    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_state_class = SensorStateClass.TOTAL

    @cached_property
    def native_value(self):
        """Return the usage in the last day in litres"""
        current_usage = self.coordinator.data[self.idx].usage_rate
        _LOGGER.debug("Current oil usage %d litres/day", current_usage)
        return Decimal(f"{current_usage:.1f}")


class ForcastEmpty(SENSiTEntity, SensorEntity):
    _attr_icon = "mdi:calendar"
    _attr_name = "Forecast Empty"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @cached_property
    def native_value(self):
        """Return the number of days to empty"""
        empty_days = self.coordinator.data[self.idx].forecast_empty
        _LOGGER.debug("Tank forecast empty %d days", empty_days)
        return empty_days
        return timedelta(days=empty_days)


class OilConsumption(SENSiTEntity, SensorEntity, RestoreEntity):
    _attr_icon = "mdi:fire"
    _attr_name = "Oil Consumption"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL
    _attr_device_class = SensorDeviceClass.ENERGY

    def __init__(self, coordinator, config_entry, idx):
        super().__init__(coordinator, config_entry, idx)
        self._state = None

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return
        self._state = state.state

    @cached_property
    def state(self):
        """Return the state of the sensor."""
        update_interval = int((self.coordinator.update_interval.seconds) / 3600)
        consumption = self.coordinator.data[self.idx].usage_rate / update_interval
        if self._state is None or str(self._state) == "unavailable":
            self._state = consumption
        else:
            self._state = float(self._state) + consumption
        _LOGGER.debug("Oil consumption %.1f kWh in last %d hours", self._state, update_interval)
        return Decimal(f"{self._state:.1f}")


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
