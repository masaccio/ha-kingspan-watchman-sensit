"""
Custom integration to integrate Kingspan Watchman SENSiT with Home Assistant.

For more details about this integration, please refer to
https://github.com/masaccio/ha-kingspan-watchman-sensit
"""

import asyncio
import builtins
import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant, callback
from homeassistant.core_config import Config
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir

from .api import KingspanAPIError, SENSiTApiClient
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
from .coordinator import SENSiTConfigEntry, SENSiTDataUpdateCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)  # pylint: disable=invalid-name

_LOGGER: logging.Logger = logging.getLogger(__package__)

TO_REDACT = [
    CONF_USERNAME,
    CONF_PASSWORD,
]


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
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    username = config_entry.data.get(CONF_USERNAME)
    password = config_entry.data.get(CONF_PASSWORD)
    usage_window = config_entry.options.get(CONF_USAGE_WINDOW, DEFAULT_USAGE_WINDOW)
    kingspan_debug = config_entry.options.get(CONF_KINGSPAN_DEBUG, False)

    if username is None or not username:
        _async_create_repair_issue(hass, config_entry)
        raise ConfigEntryAuthFailed(
            "Credentials not set",
            translation_domain=DOMAIN,
            translation_key="credentials_not_set",
        )

    client = SENSiTApiClient(username, str(password), usage_window, kingspan_debug)
    try:
        credentials_ok = await client.check_credentials()
    except KingspanAPIError as e:
        if "no level data" in str(e).lower():
            _LOGGER.warning("No data available for username '%s'", username)
            _async_delete_repair_issue(hass, config_entry)
            return False
        _LOGGER.debug("Credentials check for username '%s' failed: %s", username, e)
        _async_create_repair_issue(hass, config_entry)
        raise ConfigEntryAuthFailed(
            "Credentials invalid",
            translation_domain=DOMAIN,
            translation_key="credentials_invalid",
        ) from e
    except builtins.TimeoutError as e:
        _LOGGER.debug("Credentials check for username '%s' timed out: %s", username, e)
        _async_create_repair_issue(hass, config_entry)
        raise ConfigEntryNotReady(
            "Timed out while connecting to Kingspan service",
            translation_domain=DOMAIN,
            translation_key="timed_out",
        ) from e

    if not credentials_ok:
        _LOGGER.warning("No data available for username '%s'", username)
        _async_delete_repair_issue(hass, config_entry)
        return False

    coordinator = SENSiTDataUpdateCoordinator(
        hass,
        client=client,
        config_entry=config_entry,
        update_interval=timedelta(
            hours=config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        ),
    )
    await coordinator.async_refresh()

    if not coordinator.last_update_success:  # pragma: no cover
        raise ConfigEntryNotReady

    config_entry.runtime_data = coordinator
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if config_entry.options.get(platform, True):  # pragma: no branch
            coordinator.platforms.append(platform)
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    _async_delete_repair_issue(hass, config_entry)
    config_entry.add_update_listener(async_reload_entry)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: SENSiTConfigEntry) -> bool:
    """Handle removal of an entry."""

    coordinator = getattr(config_entry, "runtime_data", None)
    if coordinator is None:
        if DOMAIN not in hass.data or config_entry.entry_id not in hass.data[DOMAIN]:
            return False
        coordinator = hass.data[DOMAIN][config_entry.entry_id]

    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:  # pragma: no branch
        hass.data.get(DOMAIN, {}).pop(config_entry.entry_id, None)
        if hasattr(config_entry, "runtime_data"):
            del config_entry.runtime_data
        _async_delete_repair_issue(hass, config_entry)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, config_entry: SENSiTConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
