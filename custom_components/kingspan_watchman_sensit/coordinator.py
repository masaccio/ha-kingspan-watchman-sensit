"""DataUpdateCoordinator for Kingspan Watchman SENSiT."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SENSiTApiClient,
    SENSiTApiClientError,
    SENSiTAuthError,
    SENSiTConnectionError,
    SENSiTNoDataError,
    TankData,
)
from .const import CONF_USERNAME, DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__package__)

type SENSiTConfigEntry = ConfigEntry[SENSiTDataUpdateCoordinator]  # pylint: disable=invalid-name


class SENSiTDataUpdateCoordinator(DataUpdateCoordinator[list[TankData]]):
    """Class to manage fetching data from the API."""

    config_entry: SENSiTConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SENSiTConfigEntry,
        client: SENSiTApiClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.api = client
        self._unavailable_logged = False
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> list[TankData]:
        """Update data via API."""
        try:
            data = await self.api.async_get_data()
        except SENSiTAuthError as err:
            raise ConfigEntryAuthFailed(
                "Credentials invalid",
                translation_domain=DOMAIN,
                translation_key="credentials_invalid",
            ) from err
        except SENSiTNoDataError:
            username = self.config_entry.data.get(CONF_USERNAME)
            _LOGGER.warning("No data available for username '%s'", username)
            return []
        except (SENSiTConnectionError, SENSiTApiClientError) as err:
            if not self._unavailable_logged:
                _LOGGER.warning("Error communicating with Kingspan API: %s", err)
                self._unavailable_logged = True

            if isinstance(err, SENSiTConnectionError):
                raise UpdateFailed(
                    "Timed out while connecting to the Kingspan service",
                    translation_domain=DOMAIN,
                    translation_key="timed_out",
                ) from err

            raise UpdateFailed(f"Failed to fetch data from API: {err}") from err

        if self._unavailable_logged:
            _LOGGER.info("Kingspan service is available again")
            self._unavailable_logged = False
        return data
