"""API Client for Kingspan Watchman SENSiT."""

# pylint: disable=too-many-instance-attributes

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypedDict, cast

from connectsensor import __version__ as api_version
from connectsensor.client import APIVersion, AsyncSensorClient
from connectsensor.exceptions import (
    KingspanAPIError,
    KingspanInvalidCredentialsError,
    KingspanTimeoutError,
)
from homeassistant.util.dt import as_local
from httpx import HTTPError
from httpx import TimeoutException as HttpxTimeoutException

from .const import API_TIMEOUT, DEFAULT_USAGE_WINDOW, REFILL_THRESHOLD

_LOGGER: logging.Logger = logging.getLogger(__package__)
_LOGGER.debug("AsyncSensorClient loaded from %s", inspect.getfile(AsyncSensorClient))


class SENSiTApiClientError(Exception):
    """Base exception for SENSiT API client errors."""


class SENSiTAuthError(SENSiTApiClientError):
    """Exception raised for authentication errors."""


class SENSiTConnectionError(SENSiTApiClientError):
    """Exception raised for connection or timeout errors."""


class SENSiTNoDataError(SENSiTApiClientError):
    """Exception raised when the account has no tank level data."""


class TankHistoryPoint(TypedDict):
    """Single point of tank history returned by the Kingspan API."""

    level_litres: float
    reading_date: datetime


@dataclass(slots=True)
class TankData:
    """Structured tank data returned by the Kingspan API."""

    level: float = 0.0
    serial_number: str = ""
    model: str = ""
    name: str = ""
    capacity: float = 0.0
    last_read: datetime | None = None
    history: list[TankHistoryPoint] = field(default_factory=list)
    usage_rate: float = 0.0
    forecast_empty: int = 0


class SENSiTApiClient:
    """Wrapper around the Kingspan Connect Sensor API."""

    def __init__(
        self,
        username: str,
        password: str,
        usage_window: int = DEFAULT_USAGE_WINDOW,
        debug: bool = False,
    ) -> None:
        """Initialize the API client."""
        _LOGGER.debug("API init as username=%s [API version %s]", username, api_version)
        self._username = username
        self._password = password
        self._usage_window = usage_window

        connectsensor_logger = logging.getLogger("connectsensor")
        if debug:
            _LOGGER.debug("Enabling API debug")
            connectsensor_logger.setLevel(logging.DEBUG)
        else:
            connectsensor_logger.setLevel(logging.NOTSET)

    async def async_get_data(self) -> list[TankData]:
        """Get tank data from the API."""
        try:
            async with asyncio.timeout(API_TIMEOUT):
                return await self._get_tank_data()
        except KingspanInvalidCredentialsError as err:
            raise SENSiTAuthError(f"Invalid credentials for {self._username}: {err}") from err
        except KingspanTimeoutError, TimeoutError, HttpxTimeoutException, HTTPError:
            raise SENSiTConnectionError(
                f"Timeout or connection error fetching data for {self._username}"
            ) from None
        except KingspanAPIError as err:
            if "no level data" in str(err).lower():
                raise SENSiTNoDataError(f"No level data available for {self._username}") from err
            raise SENSiTApiClientError(
                f"API error fetching data for {self._username}: {err}"
            ) from err
        except Exception:
            _LOGGER.exception("Unhandled error fetching data for %s", self._username)
            raise SENSiTApiClientError(
                f"Unhandled error fetching data for {self._username}"
            ) from None

    async def check_credentials(self) -> bool:
        """Verify credentials with the Kingspan service."""
        try:
            async with asyncio.timeout(API_TIMEOUT):
                async with AsyncSensorClient(version=APIVersion.KNECT_V1) as client:
                    await client.login(self._username, self._password)
        except KingspanInvalidCredentialsError:
            raise SENSiTAuthError(f"Invalid credentials for {self._username}") from None
        except (KingspanTimeoutError, TimeoutError, HttpxTimeoutException, HTTPError) as err:
            raise SENSiTConnectionError(f"Timeout logging in as {self._username}") from err
        except KingspanAPIError as err:
            raise SENSiTAuthError(f"API error logging in as {self._username}") from err
        except Exception as err:
            raise SENSiTConnectionError(f"Unhandled error logging in as {self._username}") from err
        return True

    async def _get_tank_data(self) -> list[TankData]:
        """Fetch and parse all tank data from the API."""
        _LOGGER.debug("Fetching tank data with username=%s", self._username)
        async with AsyncSensorClient(version=APIVersion.KNECT_V1) as client:
            await client.login(self._username, self._password)
            tanks = await client.tanks
            results: list[TankData] = []

            for tank in tanks:
                raw_history = await tank.history()
                filtered = filter_history(
                    raw_history, self._usage_window  # pyright: ignore[reportArgumentType]
                )

                rate = self._calculate_usage_rate(filtered)
                forecast = self._calculate_forecast_empty(filtered, rate)

                if not raw_history:
                    _LOGGER.warning("No history: usage and forecast unavailable")

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
                _LOGGER.debug(
                    "Tank data: name='%s', level=%d, capacity=%d, serial_number=%s, "
                    "last_read=%s, usage_rate=%.1f, forecast_empty=%d",
                    tank_data.name,
                    tank_data.level,
                    tank_data.capacity,
                    tank_data.serial_number,
                    tank_data.last_read,
                    tank_data.usage_rate,
                    tank_data.forecast_empty,
                )
                results.append(tank_data)

            return results

    @staticmethod
    def _calculate_usage_rate(history: list[TankHistoryPoint]) -> float:
        """Calculate the average daily usage rate over the filtered window."""
        if len(history) < 2:
            return 0.0

        delta_levels: list[float] = []
        current_level = history[0]["level_litres"]
        for row in history[1:]:
            # Ignore refill days where oil goes up significantly
            if current_level != 0 and (row["level_litres"] / current_level) < REFILL_THRESHOLD:
                delta_levels.append(current_level - row["level_litres"])
            current_level = row["level_litres"]

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
