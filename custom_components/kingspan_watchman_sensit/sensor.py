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

from .const import CONF_OIL_ENERGY_DENSITY, DEFAULT_OIL_ENERGY_DENSITY, DOMAIN
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
            CurrentEnergyUsage(coordinator, config_entry, idx),
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


class CurrentEnergyUsage(SENSiTEntity, SensorEntity):
    """Oil consumption in kWh from litres/day sensor."""

    _attr_icon: str | None = "mdi:fire"
    _attr_name: str | None = "Current Energy Usage"
    _attr_device_class: SensorDeviceClass | str | None = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement: str | None = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class: SensorStateClass | str | None = SensorStateClass.TOTAL

    def __init__(self, coordinator, config_entry, idx):
        super().__init__(coordinator, config_entry, idx)
        self._config_entry = config_entry

    @property
    def native_value(self) -> float | None:
        """Return energy usage in kWh from litres/day data."""
        litres_per_day = self.coordinator.data[self.idx].usage_rate
        energy_density = self._config_entry.options.get(
            CONF_OIL_ENERGY_DENSITY,
            self._config_entry.data.get(
                CONF_OIL_ENERGY_DENSITY,
                DEFAULT_OIL_ENERGY_DENSITY,
            ),
        )
        kwh_per_day = float(litres_per_day * energy_density)
        return round(kwh_per_day, 1)


class OilConsumption(SENSiTEntity, SensorEntity, RestoreEntity):
    _attr_icon: str | None = "mdi:fire"
    _attr_name: str | None = "Oil Consumption"
    _attr_native_unit_of_measurement: str | None = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class: SensorStateClass | str | None = SensorStateClass.TOTAL_INCREASING
    _attr_device_class: SensorDeviceClass | str | None = SensorDeviceClass.ENERGY

    def __init__(self, coordinator, config_entry, idx):
        super().__init__(coordinator, config_entry, idx)
        self._config_entry = config_entry
        self._consumption_total = None
        self._consumption_last_read = None

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        old_state = await self.async_get_last_state()
        if old_state:
            self._state = old_state.state
            # Ensure consumption_last_read is a string; may be datetime object
            consumption_last_read = str(old_state.attributes.get("consumption_last_read"))
            self._consumption_last_read = dt_util.parse_datetime(consumption_last_read)
            consumption_total = old_state.attributes.get("consumption_total")
            self._consumption_total = round(float(consumption_total or 0.0), 1)
            _LOGGER.debug(
                "Restoring consumption: %.1f litres at %s",
                self._consumption_total,
                self._consumption_last_read,
            )

    @property
    def extra_state_attributes(self):
        return {
            "consumption_last_read": self._consumption_last_read,
            "consumption_total": self._consumption_total,
        }

    @property
    def native_value(self):
        last_read = self.coordinator.data[self.idx].last_read
        if self._consumption_last_read is None:
            self._consumption_last_read = last_read

        if self._consumption_last_read != last_read:
            usage_rate = self.coordinator.data[self.idx].usage_rate
            energy_density = self._config_entry.options.get(
                CONF_OIL_ENERGY_DENSITY,
                self._config_entry.data.get(
                    CONF_OIL_ENERGY_DENSITY,
                    DEFAULT_OIL_ENERGY_DENSITY,
                ),
            )
            self._consumption_total += energy_density * round(usage_rate, 1)
            self._consumption_last_read = last_read

        if self._consumption_total is None:
            return None

        return Decimal(f"{self._consumption_total:.1f}")


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
