"""Sample API Client."""
import logging
from asyncio import TimeoutError
from datetime import datetime, timedelta, timezone

from async_timeout import timeout
from connectsensor import APIError, AsyncSensorClient

from .const import API_TIMEOUT, DEFAULT_USAGE_WINDOW, REFILL_THRESHOLD

_LOGGER: logging.Logger = logging.getLogger(__package__)

LOCAL_TZINFO = datetime.now(timezone.utc).astimezone().tzinfo


class TankData:
    def __init__(self):
        pass


class SENSiTApiClient:
    def __init__(
        self,
        username: str,
        password: str,
        usage_window: int = DEFAULT_USAGE_WINDOW,
        debug=False,
    ) -> None:
        """Simple API Client for ."""
        _LOGGER.debug("API init as username=%s", username)
        self._username = username
        self._password = password
        self._usage_window = usage_window
        if debug:
            _LOGGER.debug("Enabling Zeep service debug")
            _LOGGER.debug("Logger = %s", logging.getLogger("zeep.transports"))

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

    async def check_credentials(self) -> bool:
        """Login to check credentials"""
        async with timeout(API_TIMEOUT):
            async with AsyncSensorClient() as client:
                await client.login(self._username, self._password)
        return True

    async def _get_tank_data(self):
        _LOGGER.debug("Fetching tank data with username=%s", self._username)
        async with AsyncSensorClient() as client:
            await client.login(self._username, self._password)
            tanks = await client.tanks
            self.data = []
            for tank in tanks:
                tank_data = TankData()
                tank_data.level = await tank.level
                tank_data.serial_number = await tank.serial_number
                tank_data.model = await tank.model
                tank_data.name = await tank.name
                tank_data.capacity = await tank.capacity
                tank_data.last_read = await tank.last_read
                # Timestamp sensor needs timezone included
                tank_data.last_read = tank_data.last_read.replace(tzinfo=LOCAL_TZINFO)
                tank_data.history = await tank.history
                if len(tank_data.history) == 0:
                    _LOGGER.warning("No history: usage and forecast unavailable")
                    tank_data.usage_rate = 0
                    tank_data.forecast_empty = 0
                else:
                    tank_data.usage_rate = self.usage_rate(tank_data)
                    tank_data.forecast_empty = self.forecast_empty(tank_data)
                _LOGGER.debug(
                    "Tank data: level=%d, capacity=%d, serial_number=%s,"
                    + "last_read=%s, usage_rate=%.1f, forecast_empty=%s",
                    tank_data.level,
                    tank_data.capacity,
                    tank_data.serial_number,
                    tank_data.last_read,
                    tank_data.usage_rate,
                    tank_data.forecast_empty,
                )
                _LOGGER.debug("Found tank name '%s'", tank_data.name)
                self.data.append(tank_data)
            return self.data

    def usage_rate(self, tank_data: TankData):
        history = filter_history(tank_data.history, self._usage_window)
        if len(history) == 0:
            return 0

        delta_levels = []
        current_level = history[0]["level_litres"]
        for _, row in enumerate(history[1:]):
            # Ignore refill days where oil goes up significantly
            if current_level != 0 and (row["level_litres"] / current_level) < REFILL_THRESHOLD:
                delta_levels.append(current_level - row["level_litres"])

            current_level = row["level_litres"]

        if len(delta_levels) > 0:
            return sum(delta_levels) / len(delta_levels)
        else:  # pragma: no cover
            return 0

    def forecast_empty(self, tank_data: TankData):
        history = filter_history(tank_data.history, self._usage_window)
        if len(history) == 0:
            return 0

        rate = self.usage_rate(tank_data)
        if rate == 0:  # pragma: no cover
            # Avoid divide by zero in corner case of no usage
            return 0
        else:
            current_level = int(history[-1]["level_litres"])
            return int(current_level / abs(rate))


def filter_history(history: list[dict], usage_window) -> list[dict]:
    """Filter tank history to a smaller recent window of days"""
    time_delta = datetime.today() - timedelta(days=usage_window)
    time_delta = time_delta.replace(tzinfo=LOCAL_TZINFO)
    # API returns naive datetime rather than with timezones
    history = [
        dict(x, reading_date=x["reading_date"].replace(tzinfo=LOCAL_TZINFO)) for x in history
    ]
    history = [x for x in history if x["reading_date"] >= time_delta]
    return history
