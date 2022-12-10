"""Sample API Client."""
import logging

from homeassistant.helpers.update_coordinator import UpdateFailed
from connectsensor import AsyncSensorClient, APIError
from async_timeout import timeout

TIMEOUT = 10


_LOGGER: logging.Logger = logging.getLogger(__package__)

HEADERS = {"Content-type": "application/json; charset=UTF-8"}


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
            async with timeout(TIMEOUT):
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
                    return self.data
        except APIError as e:
            raise UpdateFailed() from e
        except TimeoutError as e:
            _LOGGER.error(f"Timeout error logging in as {self.username}", e)
