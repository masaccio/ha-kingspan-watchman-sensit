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
            self.data.history = await tank.history
            # Timestamp sensor needs timezone included
            self.data.last_read = self.data.last_read.replace(tzinfo=timezone.utc)
            self.data.usage_rate = usage_rate(self.data.history, REFILL_THRESHOLD)
            self.data.forecast_empty = forecast_empty(self.data.history, USAGE_WINDOW)
            _LOGGER.debug(
                "Tank data: level=%d, capacity=%d, serial_number=%s,"
                + "last_read=%s, usage_rate=%.1f, forecast_empty=%s",
                self.data.level,
                self.data.capacity,
                self.data.serial_number,
                str(self.data.last_read),
                self.data.usage_rate,
                str(self.data.forecast_empty),
            )
            return self.data


def usage_rate(history, threshold):
    if len(history) == 0:  # pragma: no cover
        return 0
    current_level = history.level_litres.iloc[0]
    if current_level == 0:  # pragma: no cover
        return 0
    delta_levels = []
    for index, row in history.iloc[1:].iterrows():
        # Ignore refill days where oil goes up by 'threshold'
        if (row.level_litres / current_level) < threshold:
            delta_levels.append(current_level - row.level_litres)
        current_level = row.level_litres
    if len(delta_levels) == 0:
        return 0
    return sum(delta_levels) / len(delta_levels)


def forecast_empty(history, window):
    time_delta = datetime.today() - timedelta(days=window)
    history = history[history.reading_date >= time_delta]

    threshold = REFILL_THRESHOLD
    rate = usage_rate(history, threshold)
    if rate == 0:  # pragma: no cover
        return 0
    else:
        current_level = int(history.level_litres.tail(1))
        return int(current_level / abs(rate))
