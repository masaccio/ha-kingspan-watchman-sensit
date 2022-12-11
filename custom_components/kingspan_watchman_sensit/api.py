"""Sample API Client."""
import logging
from asyncio import TimeoutError

from async_timeout import timeout
from connectsensor import APIError, AsyncSensorClient

from .const import API_TIMEOUT

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
            _LOGGER.error("timeout error logging in as %s", self._username)

    async def _get_tank_data(self):
        _LOGGER.debug("fetching tank data with username={self._username}")
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
            _LOGGER.debug(
                "tank data: level=%d, capacity=%d, serial_number=%s, last_read=%s",
                self.data.level,
                self.data.capacity,
                self.data.serial_number,
                str(self.data.last_read),
            )
            return self.data
