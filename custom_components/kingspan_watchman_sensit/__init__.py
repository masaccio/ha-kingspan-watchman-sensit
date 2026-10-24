"""Custom integration to integrate Kingspan Watchman SENSiT with Home Assistant."""

from __future__ import annotations

import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant, callback
from homeassistant.core_config import Config
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.httpx_client import get_async_client

from .api import SENSiTApiClient
from .const import (
    CONF_KINGSPAN_DEBUG,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_USAGE_WINDOW,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_USAGE_WINDOW,
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
    usage_window = config_entry.options.get(CONF_USAGE_WINDOW, DEFAULT_USAGE_WINDOW)
    kingspan_debug = config_entry.options.get(CONF_KINGSPAN_DEBUG, False)

    if not username or not password:
        _async_create_repair_issue(hass, config_entry)
        raise ConfigEntryAuthFailed(
            "Credentials not set",
            translation_domain=DOMAIN,
            translation_key="credentials_not_set",
        )

    httpx_client = get_async_client(hass)
    client = SENSiTApiClient(
        username=username,
        password=str(password),
        usage_window=usage_window,
        debug=kingspan_debug,
        client=httpx_client,
    )

    coordinator = SENSiTDataUpdateCoordinator(
        hass,
        client=client,
        config_entry=config_entry,
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
    unloaded = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unloaded:
        _async_delete_repair_issue(hass, config_entry)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, config_entry: SENSiTConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(config_entry.entry_id)
