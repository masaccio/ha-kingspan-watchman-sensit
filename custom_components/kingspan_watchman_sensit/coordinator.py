"""DataUpdateCoordinator for Kingspan Watchman SENSiT."""

import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

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
        self.data_stale = False
        self.last_successful_update: datetime | None = None
        self._store = Store[dict[str, Any]](hass, 1, f"{DOMAIN}.{config_entry.entry_id}")
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            config_entry=config_entry,
        )

    async def _async_setup(self) -> None:
        """Restore the last successful sensor snapshot before contacting Kingspan."""
        self.data = []
        try:
            cached = await self._store.async_load()
            username = self.config_entry.data[CONF_USERNAME].casefold()
            if not cached or cached[CONF_USERNAME] != username:
                return
            last_update = dt_util.parse_datetime(cached["last_successful_update"])
            if last_update is None or last_update.tzinfo is None:
                raise ValueError("Invalid cached update timestamp")
            tanks = []
            for snapshot in cached["tanks"]:
                tank = TankData(**snapshot)
                if not isinstance(tank.serial_number, str) or not tank.serial_number:
                    raise ValueError("Invalid cached tank serial number")
                for key in ("level", "capacity", "usage_rate", "forecast_empty"):
                    if not isinstance(snapshot[key], (int, float)):
                        raise ValueError("Invalid cached tank measurement")
                if tank.last_read is not None:
                    tank.last_read = dt_util.parse_datetime(snapshot["last_read"])
                    if tank.last_read is None or tank.last_read.tzinfo is None:
                        raise ValueError("Invalid cached reading timestamp")
                tanks.append(tank)
        except (HomeAssistantError, OSError, KeyError, TypeError, ValueError):
            _LOGGER.warning("Could not restore cached Kingspan readings", exc_info=True)
            return
        self.data = tanks
        self.last_successful_update = last_update
        self.data_stale = bool(tanks)

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
            data = []
        except (SENSiTConnectionError, SENSiTApiClientError) as err:
            if not self._unavailable_logged:
                _LOGGER.warning("Error communicating with Kingspan API: %s", err)
                self._unavailable_logged = True

            if self.data:
                self.data_stale = True
                return self.data

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
        self.data_stale = False
        self.last_successful_update = dt_util.utcnow()
        snapshots = []
        for tank in data:
            snapshot = asdict(tank)
            # History is only used by diagnostics; sensors need the calculated snapshot.
            snapshot.pop("history")
            snapshot["last_read"] = tank.last_read.isoformat() if tank.last_read else None
            snapshots.append(snapshot)
        await self._store.async_save(
            {
                CONF_USERNAME: self.config_entry.data[CONF_USERNAME].casefold(),
                "last_successful_update": self.last_successful_update.isoformat(),
                "tanks": snapshots,
            }
        )
        return data
