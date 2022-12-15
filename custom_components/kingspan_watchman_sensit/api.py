"""Sample API Client."""
import logging
from asyncio import TimeoutError
from datetime import timezone, datetime, timedelta
from async_timeout import timeout
from connectsensor import APIError, AsyncSensorClient

from .const import API_TIMEOUT, REFILL_THRESHOLD, USAGE_WINDOW

_LOGGER: logging.Logger = logging.getLogger(__package__)


class TankData:
    def __init__(self):
        pass


class SENSiTApiClient:
    def __init__(self, username: str, password: str) -> None:
        """Simple API Client for ."""
        _LOGGER.debug("API init as username=%s, password=%s", username, password)
        self._username = username
        self._password = password

    async def async_get_data(self) -> dict:
        """Get tank data from the API"""
        try:
            async with timeout(API_TIMEOUT):
                return await self._get_tank_data()
        except APIError as e:
            _LOGGER.error("API error logging in as %s: %s", self._username, str(e))
        except TimeoutError:
            _LOGGER.error("Timeout error logging in as %s", self._username)
        except Exception as e:  # pylint: disable=broad-except
            _LOGGER.error("Unhandled error logging in as %s: %s", self._username, e)

    async def _get_tank_data(self):
        _LOGGER.debug("Fetching tank data with username=%s", self._username)
        async with AsyncSensorClient() as client:
            await client.login(self._username, self._password)
            tanks = await client.tanks
            tank = tanks[0]
            self.data = TankData()
            self.data.level = await tank.level
            self.data.serial_number = await tank.serial_number
            self.data.model = await tank.model
            self.data.name = await tank.name
            self.data.capacity = await tank.capacity
            self.data.last_read = await tank.last_read
            # Timestamp sensor needs timezone included
            self.data.last_read = self.data.last_read.replace(tzinfo=timezone.utc)
            self.data.history = await tank.history
            if len(self.data.history) == 0:
                _LOGGER.warning("No history: usage and forecast unavailable")
                self.data.usage_rate = 0
                self.data.forecast_empty = 0
            else:
                self.data.usage_rate = self.usage_rate()
                self.data.forecast_empty = self.forecast_empty()
            _LOGGER.debug(
                "Tank data: level=%d, capacity=%d, serial_number=%s,"
                + "last_read=%s, usage_rate=%.1f, forecast_empty=%s",
                self.data.level,
                self.data.capacity,
                self.data.serial_number,
                self.data.last_read,
                self.data.usage_rate,
                self.data.forecast_empty,
            )
            return self.data

    def usage_rate(self):
        time_delta = datetime.today() - timedelta(days=USAGE_WINDOW)
        history = self.data.history
        history = history[history.reading_date >= time_delta]
        if len(history) == 0:
            return 0

        delta_levels = []
        current_level = history.level_litres.iloc[0]
        for index, row in history.iloc[1:].iterrows():
            # Ignore refill days where oil goes up significantly
            if (
                current_level != 0
                and (row.level_litres / current_level) < REFILL_THRESHOLD
            ):
                delta_levels.append(current_level - row.level_litres)

            current_level = row.level_litres

        if len(delta_levels) > 0:
            return sum(delta_levels) / len(delta_levels)
        else:  # pragma: no cover
            return 0

    def forecast_empty(self):
        time_delta = datetime.today() - timedelta(days=USAGE_WINDOW)
        history = self.data.history
        history = history[history.reading_date >= time_delta]
        if len(history) == 0:
            return 0

        rate = self.usage_rate()
        if rate == 0:  # pragma: no cover
            # Avoid divide by zero in corner case of no usage
            return 0
        else:
            current_level = int(history.level_litres.tail(1))
            return int(current_level / abs(rate))
