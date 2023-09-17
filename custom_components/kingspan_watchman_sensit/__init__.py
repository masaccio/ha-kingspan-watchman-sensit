"""
Custom integration to integrate Kingspan Watchman SENSiT with Home Assistant.

For more details about this integration, please refer to
https://github.com/masaccio/ha-kingspan-watchman-sensit
"""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SENSiTApiClient, APIError
from .const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORMS,
    DEFAULT_UPDATE_INTERVAL,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    _LOGGER.debug("username='%s', password='%s'", username, password)
    if username is None or not username:
        raise ConfigEntryAuthFailed(f"Credentials not set")

    client = SENSiTApiClient(username, password)
    try:
        _ = await client.check_credentials()
    except APIError as e:
        _LOGGER.debug("Credentials check for username '%s' failed: %s", username, e)
        raise ConfigEntryAuthFailed(f"Credentials invalid") from e
    except TimeoutError as e:
        _LOGGER.debug("Credentials check for username '%s' timed out: %s", username, e)
        raise ConfigEntryNotReady(
            f"Timed out while connecting to Kingspan service"
        ) from e

    coordinator = SENSiTDataUpdateCoordinator(
        hass,
        client=client,
        update_interval=timedelta(
            hours=entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        ),
    )
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if entry.options.get(platform, True):  # pragma: no branch
            coordinator.platforms.append(platform)
            hass.async_add_job(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )

    entry.add_update_listener(async_reload_entry)
    return True


class SENSiTDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SENSiTApiClient,
        update_interval=DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize."""
        self.api = client
        self.platforms = []

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.api.async_get_data()
        except Exception as exception:
            raise UpdateFailed() from exception


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:  # pragma: no branch
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
