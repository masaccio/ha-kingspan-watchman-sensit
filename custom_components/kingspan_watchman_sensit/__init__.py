"""
Custom integration to integrate Kingspan Watchman SENSiT with Home Assistant.

For more details about this integration, please refer to
https://github.com/masaccio/ha-kingspan-watchman-sensit
"""

import asyncio
import builtins
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core_config import Config
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import APIError, SENSiTApiClient
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

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    username = config_entry.data.get(CONF_USERNAME)
    password = config_entry.data.get(CONF_PASSWORD)
    usage_window = config_entry.options.get(CONF_USAGE_WINDOW, DEFAULT_USAGE_WINDOW)
    kingspan_debug = config_entry.options.get(CONF_KINGSPAN_DEBUG, False)

    if username is None or not username:
        raise ConfigEntryAuthFailed("Credentials not set")

    client = SENSiTApiClient(username, password, usage_window, kingspan_debug)
    try:
        _ = await client.check_credentials()
    except APIError as e:
        if "no level data" in str(e).lower():
            _LOGGER.warning("No data available for username '%s'", username)
        else:
            _LOGGER.debug("Credentials check for username '%s' failed: %s", username, e)
            raise ConfigEntryAuthFailed("Credentials invalid") from e
    except builtins.TimeoutError as e:
        _LOGGER.debug("Credentials check for username '%s' timed out: %s", username, e)
        raise ConfigEntryNotReady("Timed out while connecting to Kingspan service") from e

    coordinator = SENSiTDataUpdateCoordinator(
        hass,
        client=client,
        update_interval=timedelta(
            hours=config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        ),
    )
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:  # pragma: no cover
        raise ConfigEntryNotReady

    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if config_entry.options.get(platform, True):  # pragma: no branch
            coordinator.platforms.append(platform)
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    config_entry.add_update_listener(async_reload_entry)
    return True


class SENSiTDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self, hass: HomeAssistant, client: SENSiTApiClient, update_interval: timedelta
    ) -> None:
        """Initialize."""
        self.api = client
        self.platforms = []

        _LOGGER.debug("Update interval set to %s", update_interval)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self.update,
            update_interval=update_interval,
        )

    async def update(self):
        """Update data via API."""
        try:
            return await self.api.async_get_data()
        except APIError as e:
            _LOGGER.warning("APIError during update: %s", e)
            raise UpdateFailed("Failed to fetch data from API") from e


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""

    if DOMAIN not in hass.data:
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
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
