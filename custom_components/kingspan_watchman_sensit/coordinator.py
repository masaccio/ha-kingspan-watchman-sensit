"""DataUpdateCoordinator for Kingspan Watchman SENSiT."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KingspanAPIError, SENSiTApiClient, TankData
from .const import DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__package__)


class SENSiTDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: SENSiTApiClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.api = client
        self.platforms: list[str] = []
        self._unavailable_logged = False
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self.update,
            update_interval=update_interval,
            config_entry=config_entry,
        )

    async def update(self) -> list[TankData]:
        """Update data via API."""
        try:
            data = await self.api.async_get_data()
        except KingspanAPIError as e:
            _LOGGER.warning("KingspanAPIError during update: %s", e)
            self._unavailable_logged = True
            raise UpdateFailed("Failed to fetch data from API") from e

        if self._unavailable_logged:
            _LOGGER.info("Kingspan service is available again")
            self._unavailable_logged = False
        return data
