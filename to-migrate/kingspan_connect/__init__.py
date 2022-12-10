"""
Custom integration to integrate Kingspan SENSiT with Home Assistant.
"""

import logging

from async_timeout import timeout
from asyncio import gather, TimeoutError
from connectsensor import AsyncSensorClient, APIError
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
    TIMEOUT,
)

SCAN_INTERVAL = timedelta(hours=12)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    coordinator = KingspanConnectDataUpdateCoordinator(hass, username, password)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            coordinator.platforms.append(platform)
            hass.async_add_job(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


class TankData:
    def __init__(self):
        pass

    # def __setattr__(self, name: str, value) -> None:
    #     setattr(self, name, value)


class KingspanConnectDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Connect Sensor API."""

    def __init__(self, hass: HomeAssistant, username: str, password: str) -> None:
        """Initialize."""
        self.username = username
        self.password = password
        self.platforms = []

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            async with timeout(TIMEOUT):
                async with AsyncSensorClient() as client:
                    await client.login(self.username, self.password)
                    tanks = await client.tanks
                    tank = tanks[0]
                    self.data = TankData()
                    self.data.level = await tank.level
                    self.data.serial_number = await tank.serial_number
                    self.data.model = await tank.model
                    self.data.name = await tank.name
                    self.data.capacity = await tank.capacity
                    self.data.last_read = await tank.last_read
                    return self.data
        except APIError as e:
            raise UpdateFailed() from e
        except TimeoutError as e:
            _LOGGER.error(f"Timeout error logging in as {self.username}", e)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(
        await gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)