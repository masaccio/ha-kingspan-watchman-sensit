"""Development platform to monkey-patch API exceptions."""

# pylint: disable=abstract-method

import logging
from datetime import timedelta

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo

from .api import (  # type: ignore[import-not-found] # pylint: disable=E0402
    SENSiTApiClientError,
    SENSiTAuthError,
    SENSiTConnectionError,
    SENSiTNoDataError,
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


async def async_setup_entry(_hass, config_entry, async_add_entities):
    """Set up the mock exception switches."""
    coordinator = config_entry.runtime_data

    # Preserve the original method safely
    if not hasattr(coordinator.api, "original_async_get_data"):
        coordinator.api.original_async_get_data = coordinator.api.async_get_data

    switches: list[SwitchEntity] = [
        MockExceptionSwitch(coordinator, key, exc) for key, exc in MOCK_EXCEPTIONS.items()
    ]
    switches.append(FastPollingSwitch(coordinator, config_entry))

    async_add_entities(switches)


class FastPollingSwitch(SwitchEntity):
    """Switch to force a 1-minute update interval for development."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, config_entry):
        """Initialize the fast polling switch."""
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._attr_name = "Force Fast Polling (1 min)"

        # Link to the first tank's device
        serial_no = coordinator.data[0].serial_number
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial_no)})
        self._attr_unique_id = f"dev_mock_fast_polling_{serial_no}"

        self._attr_icon = "mdi:bug"
        self._attr_is_on = False

    async def async_turn_on(self, **kwargs):
        """Set polling interval to 1 minute."""
        self._attr_is_on = True
        self.coordinator.update_interval = timedelta(minutes=1)
        self.async_write_ha_state()
        _LOGGER.warning("Dev Mode: Polling interval reduced to 1 minute.")

        # Force an immediate refresh to reset the internal timer
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Restore normal polling interval from config."""
        self._attr_is_on = False
        hours = self.config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        self.coordinator.update_interval = timedelta(hours=hours)
        self.async_write_ha_state()
        _LOGGER.warning("Dev Mode: Polling interval restored to %s hours.", hours)

        # Force an immediate refresh to reset the internal timer
        await self.coordinator.async_request_refresh()


class MockExceptionSwitch(SwitchEntity):
    """Switch that forces the API to raise a specific exception."""

    # pylint: disable=too-many-instance-attributes

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, exception_key, exception_obj):
        """Initialize the mock exception switch."""
        self.coordinator = coordinator
        self._exception_key = exception_key
        self._exception_obj = exception_obj
        self._attr_name = exception_key.replace("_", " ").title()

        # Link to the first tank's device
        serial_no = coordinator.data[0].serial_number
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial_no)})
        self._attr_unique_id = f"dev_mock_{exception_key}_{serial_no}"

        self._attr_icon = "mdi:bug"
        self._attr_is_on = False

    async def async_turn_on(self, **kwargs):
        """Enable the monkey patch for this specific exception."""
        self._attr_is_on = True

        async def patched_get_data(*_args, **_kwargs):
            _LOGGER.warning("Monkey patch triggered: Raising %s", self._exception_key)
            raise self._exception_obj

        self.coordinator.api.async_get_data = patched_get_data
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Restore the original API method."""
        self._attr_is_on = False
        self.coordinator.api.async_get_data = self.coordinator.api.original_async_get_data
        self.async_write_ha_state()
