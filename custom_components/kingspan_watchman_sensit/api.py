"""Sample API Client."""
import logging

from connectsensor import AsyncSensorClient, APIError
from asyncio import TimeoutError
from async_timeout import timeout

from .const import API_TIMEOUT

_LOGGER: logging.Logger = logging.getLogger(__package__)


class TankData:
    def __init__(self):
        pass


class SENSiTApiClient:
    def __init__(self, username: str, password: str) -> None:
        """Simple API Client for ."""
        self._username = username
        self._password = password

    async def async_get_data(self) -> dict:
        """Get tank data from the API"""
        try:
            async with timeout(API_TIMEOUT):
                return await self._get_tank_data()
        except APIError as e:
            _LOGGER.error(f"API error logging in as {self._username}: {e}")
        except TimeoutError:
            _LOGGER.error(f"Timeout error logging in as {self._username}")

    async def _get_tank_data(self):
        async with AsyncSensorClient() as client:
            _LOGGER.debug(f"login: username={self._username}")
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
            _LOGGER.debug(f"_get_tank_data: level={self.data.level}")
            return self.data
