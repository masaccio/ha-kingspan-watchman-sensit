"""DataUpdateCoordinator for Kingspan Watchman SENSiT."""

import inspect
import logging
from collections.abc import Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypedDict, cast

import httpx
from connectsensor.client import APIVersion, AsyncSensorClient
from connectsensor.exceptions import KingspanAPIError, KingspanErrorCode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import as_local

from .const import (
    API_TIMEOUT,
    CONF_PASSWORD,
    CONF_USAGE_WINDOW,
    CONF_USERNAME,
    DEFAULT_USAGE_WINDOW,
    DOMAIN,
    REFILL_THRESHOLD,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)
_LOGGER.debug("AsyncSensorClient loaded from %s", inspect.getfile(AsyncSensorClient))

type SENSiTConfigEntry = ConfigEntry[SENSiTDataUpdateCoordinator]  # pylint: disable=invalid-name


class TankHistoryPoint(TypedDict):
    """Single point of tank history returned by the Kingspan API."""

    level_litres: float
    reading_date: datetime


@dataclass(slots=True)
class TankData:  # pylint: disable=too-many-instance-attributes
    """Structured tank data built by the Coordinator."""

    level: float = 0.0
    serial_number: str = ""
    model: str = ""
    name: str = ""
    capacity: float = 0.0
    last_read: datetime | None = None
    history: list[TankHistoryPoint] = field(default_factory=list)
    usage_rate: float = 0.0
    forecast_empty: int = 0


def filter_history(
    history: list[TankHistoryPoint] | None, usage_window: int
) -> list[TankHistoryPoint]:
    """Filter tank history to a smaller recent window of days, sorted chronologically."""
    if not history:
        return []

    cutoff = as_local(datetime.today() - timedelta(days=usage_window))
    filtered_history: list[TankHistoryPoint] = [
        {
            "level_litres": point["level_litres"],
            "reading_date": as_local(point["reading_date"]),
        }
        for point in history
    ]
    recent = [point for point in filtered_history if point["reading_date"] >= cutoff]
    recent.sort(key=lambda x: x["reading_date"])
    return recent


class SENSiTDataUpdateCoordinator(DataUpdateCoordinator[list[TankData]]):
    """Class to manage fetching data from the API."""

    config_entry: SENSiTConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SENSiTConfigEntry,
        httpx_client: httpx.AsyncClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self._httpx_client = httpx_client
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
        username = self.config_entry.data[CONF_USERNAME]
        password = self.config_entry.data[CONF_PASSWORD]
        usage_window = self.config_entry.options.get(CONF_USAGE_WINDOW, DEFAULT_USAGE_WINDOW)

        try:
            async with AsyncSensorClient(
                version=APIVersion.KNECT_V1,
                client=self._httpx_client,
                timeout=API_TIMEOUT,
            ) as client:
                await client.login(username, password)
                tanks = await client.tanks
                results: list[TankData] = []

                for tank in tanks:
                    tank.clear_cache()
                    raw_history = await tank.history()
                    filtered = filter_history(raw_history, usage_window)  # pyright: ignore[reportArgumentType]

                    rate = self._calculate_usage_rate(filtered)
                    forecast = self._calculate_forecast_empty(filtered, rate)

                    tank_data = TankData(
                        level=float(await cast(Awaitable[float], tank.level)),
                        serial_number=str(await cast(Awaitable[str], tank.serial_number)),
                        model=str(await cast(Awaitable[str], tank.model)),
                        name=str(await cast(Awaitable[str], tank.name)),
                        capacity=float(await cast(Awaitable[float], tank.capacity)),
                        last_read=as_local(await cast(Awaitable[datetime], tank.last_read)),
                        history=raw_history or [],  # pyright: ignore[reportArgumentType]
                        usage_rate=rate,
                        forecast_empty=forecast,
                    )
                    results.append(tank_data)

        except KingspanAPIError as err:
            if err.code == KingspanErrorCode.AUTH_FAILED:
                raise ConfigEntryAuthFailed(
                    "Credentials invalid",
                    translation_domain=DOMAIN,
                    translation_key="credentials_invalid",
                ) from err

            if err.code == KingspanErrorCode.NO_DATA:
                _LOGGER.warning("No data available for username '%s'", username)
                return []

            if not self._unavailable_logged:
                _LOGGER.warning("Error communicating with Kingspan API: %s", err.message)
                self._unavailable_logged = True

            if err.code == KingspanErrorCode.TIMEOUT:
                raise UpdateFailed(
                    "Timed out while connecting to the Kingspan service",
                    translation_domain=DOMAIN,
                    translation_key="timed_out",
                ) from err

            raise UpdateFailed(f"Failed to fetch data from API: {err.message}") from err

        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching Kingspan data: {err}") from err

        if self._unavailable_logged:
            _LOGGER.info("Kingspan service is available again")
            self._unavailable_logged = False

        return results

    @staticmethod
    def _calculate_usage_rate(history: list[TankHistoryPoint]) -> float:
        """Calculate the average daily usage rate over the filtered window."""
        if len(history) < 2:
            return 0.0

        delta_levels: list[float] = []
        current_level = history[0]["level_litres"]
        for row in history[1:]:
            if current_level != 0 and (row["level_litres"] / current_level) < REFILL_THRESHOLD:
                delta_levels.append(current_level - row["level_litres"])
            current_level = row["level_litres"]

        # Coverage note: a corner case that should never happen in reality:
        # two data history data points and one is a refill
        if not delta_levels:  # pragma: no cover
            return 0.0

        return sum(delta_levels) / len(delta_levels)

    @staticmethod
    def _calculate_forecast_empty(history: list[TankHistoryPoint], rate: float) -> int:
        """Estimate how many days until the tank is empty."""
        if not history or rate == 0:
            return 0

        current_level = int(history[-1]["level_litres"])
        return int(current_level / abs(rate))
