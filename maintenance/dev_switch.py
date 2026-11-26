"""Development platform to monkey-patch API exceptions and mock data."""

import logging
import random
from datetime import timedelta
from typing import cast

from homeassistant.components.number import NumberEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt as dt_util

from .api import (  # type: ignore[import-not-found] # pylint: disable=E0402
    SENSiTApiClientError,
    SENSiTAuthError,
    SENSiTConnectionError,
    SENSiTNoDataError,
    TankData,
)
from .const import (  # type: ignore[import-not-found] # pylint: disable=E0402
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

MOCK_EXCEPTIONS = {
    "force_timeout_error": SENSiTConnectionError("Simulated Timeout"),
    "force_auth_error": SENSiTAuthError("Simulated Auth Failure"),
    "force_api_error": SENSiTApiClientError("Simulated API Error"),
    "force_no_data_error": SENSiTNoDataError("No level data available (Simulated)"),
}


def _generate_mock_tanks(settings: dict) -> list[TankData]:  # pylint: disable=too-many-locals
    """Generate N mock tanks with simulated history going backwards in time."""
    tanks = []
    now = dt_util.now()
    tank_count = int(settings["mock_tank_count"])
    usage_rate = float(settings["usage_rate"])
    hist_len = int(settings["history_events"])
    refills = int(settings["refill_events"])

    for i in range(tank_count):
        history = []
        current_level = 1500.0

        # Calculate roughly how many days between each refill
        refill_interval = hist_len / (refills + 1) if refills > 0 else -1

        for j in range(hist_len):
            reading_date = now - timedelta(days=j)

            is_refill = False
            if refill_interval > 0:
                for r in range(1, refills + 1):
                    if int(r * refill_interval) == j:
                        is_refill = True
                        break

            if is_refill:
                # Tank was empty *before* the refill occurred
                current_level = 300.0
            else:
                # Going back in time, the level increases by the usage rate
                current_level += usage_rate

            history.append({"level_litres": float(current_level), "reading_date": reading_date})

        latest_level = cast("float", history[0]["level_litres"]) if history else 0.0
        tanks.append(
            TankData(
                level=latest_level,
                serial_number=f"mock_tank_{i + 1}",
                model="Mock Model",
                name=f"Mock Tank {i + 1}",
                capacity=2000.0,
                last_read=now,
                history=history,
                usage_rate=usage_rate,
                forecast_empty=int(latest_level / usage_rate) if usage_rate > 0 else 0,
            )
        )
    return tanks


def ensure_monkey_patch(coordinator):
    """Ensure the API is patched only once and initialize settings state."""
    if hasattr(coordinator, "mock_settings"):
        return

    coordinator.mock_settings = {
        "force_timeout_error": 0.0,
        "force_auth_error": 0.0,
        "force_api_error": 0.0,
        "force_no_data_error": 0.0,
        "mock_tank_count": 0.0,
        "usage_rate": 10.0,
        "history_events": 14.0,
        "refill_events": 1.0,
    }

    coordinator.api.original_async_get_data = coordinator.api.async_get_data

    async def patched_get_data(*args, **kwargs):
        settings = coordinator.mock_settings

        # Roll the dice for errors based on configured % probability
        for key, exc in MOCK_EXCEPTIONS.items():
            if random.random() * 100 < settings[key]:
                _LOGGER.warning("Dev Mode: Randomly raising %s (%s%% chance)", key, settings[key])
                raise exc

        # If no errors hit, fetch the real tank(s)
        data = await coordinator.api.original_async_get_data(*args, **kwargs)

        # Append any requested mock tanks to the real data
        if int(settings["mock_tank_count"]) > 0:
            data.extend(_generate_mock_tanks(settings))

        return data

    coordinator.api.async_get_data = patched_get_data


async def async_setup_entry(_hass, config_entry, async_add_entities):
    """Set up the mock UI controls dynamically based on the active platform."""
    coordinator = config_entry.runtime_data
    ensure_monkey_patch(coordinator)

    # Expose entities based on how HA loads this file
    if __name__.endswith(".switch"):
        async_add_entities([FastPollingSwitch(coordinator, config_entry)])

    elif __name__.endswith(".number"):
        serial_no = coordinator.data[0].serial_number
        dev_info = DeviceInfo(identifiers={(DOMAIN, serial_no)})

        entities = [
            MockSettingNumber(
                coordinator, "force_timeout_error", "Timeout Error Rate", dev_info, 0, 100, 1, "%"
            ),
            MockSettingNumber(
                coordinator, "force_auth_error", "Auth Error Rate", dev_info, 0, 100, 1, "%"
            ),
            MockSettingNumber(
                coordinator, "force_api_error", "API Error Rate", dev_info, 0, 100, 1, "%"
            ),
            MockSettingNumber(
                coordinator, "force_no_data_error", "No Data Error Rate", dev_info, 0, 100, 1, "%"
            ),
            MockSettingNumber(
                coordinator, "mock_tank_count", "Mock Tank Count", dev_info, 0, 10, 1, "tanks"
            ),
            MockSettingNumber(
                coordinator, "usage_rate", "Mock Usage Rate", dev_info, 0.0, 100.0, 0.1, "L/day"
            ),
            MockSettingNumber(
                coordinator, "history_events", "Mock History Events", dev_info, 2, 60, 1, "days"
            ),
            MockSettingNumber(
                coordinator, "refill_events", "Mock Refill Events", dev_info, 0, 10, 1, "refills"
            ),
        ]
        async_add_entities(entities)


class MockSettingNumber(NumberEntity):  # pylint: disable=abstract-method,too-many-instance-attributes
    """Slider to adjust mock settings dynamically."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(  # pylint: disable=too-many-arguments, too-many-positional-arguments # noqa: PLR0913, PLR0917
        self,
        coordinator,
        key,
        name,
        device_info,
        min_v,
        max_v,
        step,
        unit,
    ):
        self.coordinator = coordinator
        self._key = key
        self._attr_name = name
        self._attr_device_info = device_info
        self._attr_unique_id = f"dev_mock_{key}_{list(device_info['identifiers'])[0][1]}"
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = "mdi:bug"

    @property
    def native_value(self):
        """Return the current slider value from the state dictionary."""
        return self.coordinator.mock_settings[self._key]

    async def async_set_native_value(self, value: float) -> None:
        """Update the monkey-patch state when the user drags the slider."""
        self.coordinator.mock_settings[self._key] = value
        self.async_write_ha_state()


class FastPollingSwitch(SwitchEntity):  # pylint: disable=abstract-method
    """Switch to force a 1-minute update interval for development."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, config_entry):
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._attr_name = "Force Fast Polling (1 min)"
        serial_no = coordinator.data[0].serial_number
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial_no)})
        self._attr_unique_id = f"dev_mock_fast_polling_{serial_no}"
        self._attr_icon = "mdi:bug"
        self._attr_is_on = False

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = True
        self.coordinator.update_interval = timedelta(minutes=1)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = False
        hours = self.config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        self.coordinator.update_interval = timedelta(hours=hours)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
