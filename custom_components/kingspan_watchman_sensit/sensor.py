"""Sensor platform for Kingspan Watchman SENSiT."""

import logging
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
from homeassistant.util import dt as dt_util

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
            ForecastEmpty(coordinator, config_entry, idx),
            OilConsumption(coordinator, config_entry, idx),
        ]
    async_add_entities(entities)


class OilLevel(SENSiTEntity, SensorEntity):
    _attr_icon: str | None = "mdi:gauge"
    _attr_name: str | None = "Oil Level"
    _attr_device_class = SensorDeviceClass.VOLUME_STORAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS

    @property
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
    _attr_name: str | None = "Tank Percentage Full"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.TOTAL

    @property
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
    _attr_icon: str | None = "mdi:gauge-full"
    _attr_name: str | None = "Tank Capacity"
    _attr_device_class: SensorStateClass | str | None = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement: str | None = UnitOfVolume.LITERS
    _attr_state_class: SensorStateClass | str | None = SensorStateClass.TOTAL

    @property
    def native_value(self):
        """Return the tank capacity in litres"""
        _LOGGER.debug(
            "Read tank capacity: %d litres",
            self.coordinator.data[self.idx].capacity,
        )
        return self.coordinator.data[self.idx].capacity


class LastReadDate(SENSiTEntity, SensorEntity):
    _attr_icon = "mdi:clock-outline"
    _attr_name = "Last Reading Date"
    _attr_device_class: SensorStateClass | str | None = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        """Return date of the last reading"""
        _LOGGER.debug("Tank last read %s", str(self.coordinator.data[self.idx].last_read))
        return self.coordinator.data[self.idx].last_read


class CurrentUsage(SENSiTEntity, SensorEntity):
    _attr_icon: str | None = "mdi:gauge-full"
    _attr_name: str | None = "Current Usage"
    _attr_device_class: SensorStateClass | str | None = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement: str | None = UnitOfVolume.LITERS
    _attr_state_class: SensorStateClass | str | None = SensorStateClass.TOTAL

    @property
    def native_value(self):
        """Return the usage in the last day in litres"""
        current_usage = self.coordinator.data[self.idx].usage_rate
        _LOGGER.debug("Current oil usage %d litres/day", current_usage)
        return Decimal(f"{current_usage:.1f}")


class ForecastEmpty(SENSiTEntity, SensorEntity):
    _attr_icon: str | None = "mdi:calendar"
    _attr_name: str | None = "Forecast Empty"
    _attr_native_unit_of_measurement: str | None = UnitOfTime.DAYS
    _attr_state_class: SensorStateClass | str | None = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the number of days to empty"""
        empty_days = self.coordinator.data[self.idx].forecast_empty
        _LOGGER.debug("Tank forecast empty %d days", empty_days)
        return empty_days


class OilConsumption(SENSiTEntity, SensorEntity, RestoreEntity):
    _attr_icon: str | None = "mdi:fire"
    _attr_name: str | None = "Oil Consumption (per hour)"
    _attr_native_unit_of_measurement: str | None = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class: SensorStateClass | str | None = SensorStateClass.TOTAL
    _attr_device_class: SensorDeviceClass | str | None = SensorDeviceClass.ENERGY

    def __init__(self, coordinator, config_entry, idx):
        super().__init__(coordinator, config_entry, idx)
        self._consumption_rate = None
        self._last_update_time = None
        self._last_level = None

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        old_state = await self.async_get_last_state()
        if old_state:
            self._state = old_state.state
            # Ensure last_update_time is a string; may be datetime object
            last_update_time = str(old_state.attributes.get("last_update_time"))
            last_level = old_state.attributes.get("last_level")
            self._last_update_time = dt_util.parse_datetime(last_update_time)
            self._last_level = last_level
            if last_level is not None:
                _LOGGER.debug(
                    "Oil consumption: last level seen %d litres at %s", last_level, last_update_time
                )

    @property
    def extra_state_attributes(self):
        return {
            "last_update_time": self._last_update_time,
            "last_level": self._last_level,
        }

    @property
    def native_value(self):
        now = dt_util.utcnow()
        level = self.coordinator.data[self.idx].level
        if self._last_update_time and self._last_level is not None and level < self._last_level:
            # Wait until we have a new level reading and ignore tank refills
            time_delta = (now - self._last_update_time).total_seconds() / 3600
            if time_delta >= 1.0:
                # Wait until we've got an hour of data
                consumption = (self._last_level - level) / time_delta
                self._consumption_rate = Decimal(f"{consumption:.1f}")
                self._last_update_time = now
                self._last_level = level
                _LOGGER.debug("Oil consumption %.1f kWh in last %d hours", consumption, time_delta)
        else:
            _LOGGER.debug("Cannot calculate oil consumption")
            self._consumption_rate = None

        return self._consumption_rate


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
