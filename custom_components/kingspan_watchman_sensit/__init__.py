"""Custom integration to integrate Kingspan Watchman SENSiT with Home Assistant."""

from __future__ import annotations

import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant, callback
from homeassistant.core_config import Config
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    CONF_KINGSPAN_DEBUG,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import (
    SENSiTConfigEntry,
    SENSiTDataUpdateCoordinator,
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)  # pylint: disable=invalid-name

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(_hass: HomeAssistant, _config: Config) -> bool:
    """Set up this integration using YAML is not supported."""
    return True


@callback
def _async_create_repair_issue(hass: HomeAssistant, config_entry: SENSiTConfigEntry) -> None:
    """Create a repair issue for an entry that cannot authenticate."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"credentials_{config_entry.entry_id}",
        is_fixable=True,
        is_persistent=True,
        issue_domain=DOMAIN,
        severity=ir.IssueSeverity.WARNING,
        translation_key="auth_failed",
        translation_placeholders={"title": config_entry.title},
    )


@callback
def _async_delete_repair_issue(hass: HomeAssistant, config_entry: SENSiTConfigEntry) -> None:
    """Delete the repair issue for a config entry when it has been fixed."""
    ir.async_delete_issue(hass, DOMAIN, f"credentials_{config_entry.entry_id}")


async def async_setup_entry(hass: HomeAssistant, config_entry: SENSiTConfigEntry) -> bool:
    """Set up this integration using UI."""
    username = config_entry.data.get(CONF_USERNAME)
    password = config_entry.data.get(CONF_PASSWORD)

    if not username or not password:
        _async_create_repair_issue(hass, config_entry)
        raise ConfigEntryAuthFailed(
            "Credentials not set",
            translation_domain=DOMAIN,
            translation_key="credentials_not_set",
        )

    # Configure upstream debug logging based on options flow
    kingspan_debug = config_entry.options.get(CONF_KINGSPAN_DEBUG, False)
    connectsensor_logger = logging.getLogger("connectsensor")
    if kingspan_debug:
        _LOGGER.debug("Enabling Kingspan API debug")
        connectsensor_logger.setLevel(logging.DEBUG)
    else:
        connectsensor_logger.setLevel(logging.NOTSET)

    coordinator = SENSiTDataUpdateCoordinator(
        hass,
        config_entry=config_entry,
        httpx_client=get_async_client(hass),
        update_interval=timedelta(
            hours=config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        ),
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        _async_create_repair_issue(hass, config_entry)
        raise

    if not coordinator.data:
        _async_delete_repair_issue(hass, config_entry)
        return False

    config_entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    _async_delete_repair_issue(hass, config_entry)
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: SENSiTConfigEntry) -> bool:
    """Handle removal of an entry."""
    # Coverage note: move to async_unload_platforms_or_raise() so this test is not required.
    if unloaded := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):  # pragma: no branch
        _async_delete_repair_issue(hass, config_entry)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, config_entry: SENSiTConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_remove_config_entry_device(
    _hass: HomeAssistant,
    config_entry: SENSiTConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow manual removal of stale devices via the UI."""
    coordinator = config_entry.runtime_data
    active_serials = {tank.serial_number for tank in coordinator.data}

    for identifier in device_entry.identifiers:
        if identifier[0] == DOMAIN and identifier[1] in active_serials:
            return False

    return True
