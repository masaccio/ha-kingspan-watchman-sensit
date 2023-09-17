"""Global fixtures for Kingspan Watchman SENSiT integration."""
import random
import pytest
import pytest_asyncio

from async_property import async_property
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from connectsensor import APIError

from .const import (
    MOCK_TANK_LEVEL,
    MOCK_TANK_SERIAL_NUMBER,
    MOCK_TANK_MODEL,
    MOCK_TANK_NAME,
    MOCK_TANK_CAPACITY,
    HistoryType,
)


pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture enables loading custom integrations in all tests.
@pytest_asyncio.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


# This fixture is used to prevent HomeAssistant from attempting to create and
# dismiss persistent notifications. These calls would fail without this fixture
# since the persistent_notification integration is never loaded during a test.
@pytest_asyncio.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


# This fixture, when used, will result in calls to async_get_data to return None. To have the call
# return a value, we would add the `return_value=<VALUE_TO_RETURN>` parameter to the patch call.
@pytest_asyncio.fixture(name="bypass_get_data")
def bypass_get_data_fixture():
    """Skip calls to get data from API."""
    with patch(
        "custom_components.kingspan_watchman_sensit.SENSiTApiClient.async_get_data"
    ), patch(
        "custom_components.kingspan_watchman_sensit.SENSiTApiClient.check_credentials"
    ):
        yield


# In this fixture, we are forcing calls to async_get_data to raise an Exception. This is useful
# for exception handling.
@pytest_asyncio.fixture(name="error_on_get_data")
def error_get_data_fixture():
    """Simulate error when retrieving data from API."""
    with patch(
        "custom_components.kingspan_watchman_sensit.SENSiTApiClient.async_get_data",
        side_effect=Exception,
    ), patch(
        "custom_components.kingspan_watchman_sensit.SENSiTApiClient.check_credentials"
    ):
        yield


@pytest_asyncio.fixture(name="error_sensor_client")
def error_sensor_client_fixture():
    """Throw an exception from a mock AsyncSensorClient"""
    with patch(
        "custom_components.kingspan_watchman_sensit.SENSiTApiClient.check_credentials",
        side_effect=APIError,
    ) as mock_client:
        yield


@pytest_asyncio.fixture(name="timeout_sensor_client")
def timeout_sensor_client_fixture():
    """Throw an exception from a mock AsyncSensorClient"""
    with patch(
        "custom_components.kingspan_watchman_sensit.SENSiTApiClient.check_credentials",
        side_effect=TimeoutError,
    ) as mock_client:
        yield


def decreasing_history(start_date: datetime) -> list:
    history = []
    start_date = start_date.replace(
        hour=0, minute=30, second=0, microsecond=0
    ) - timedelta(days=30)

    for day in range(1, 20):
        percent = 100 - (day * 5) + random.randint(0, 3)
        level = int(MOCK_TANK_CAPACITY * (percent / 100))
        reading_date = start_date + timedelta(days=day)
        history.append(
            {
                "reading_date": reading_date,
                "level_percent": percent,
                "level_litres": level,
            }
        )
    # Refill happens
    for day in range(20, 31):
        percent = 100 - ((day - 20) * 5) + random.randint(0, 3)
        level = int(MOCK_TANK_CAPACITY * (percent / 100))
        reading_date = start_date + timedelta(days=day)
        history.append(
            {
                "reading_date": reading_date,
                "level_percent": percent,
                "level_litres": level,
            }
        )
    return history


class MockAsyncTank:
    """Mock SENSiT tank with options for different tank level/history data"""

    def __init__(
        self,
        *args,
        tank_level=MOCK_TANK_LEVEL,
        history_type=HistoryType.DECREASING,
        tank_num=None,
    ):
        super().__init__(*args)
        self._level = tank_level
        self._history_type = history_type
        self._tank_num = tank_num

    @async_property
    async def level(self) -> int:
        return self._level

    @async_property
    async def serial_number(self) -> str:
        if self._tank_num is None:
            return MOCK_TANK_SERIAL_NUMBER
        else:
            return MOCK_TANK_SERIAL_NUMBER + f"-{self._tank_num}"

    @async_property
    async def model(self) -> str:
        return MOCK_TANK_MODEL

    @async_property
    async def name(self) -> str:
        if self._tank_num is None:
            return MOCK_TANK_NAME
        else:
            return MOCK_TANK_NAME + f" #{self._tank_num}"

    @async_property
    async def capacity(self) -> int:
        return MOCK_TANK_CAPACITY

    @async_property
    async def last_read(self) -> str:
        history = await self.history
        if len(history) > 0:
            return history[-1]["reading_date"]
        else:
            return datetime.now()

    @async_property
    async def history(self) -> str:
        # Build a month of history with a refill halfway through
        if self._history_type == HistoryType.DECREASING:
            return decreasing_history(datetime.now())
        elif self._history_type == HistoryType.EXPIRED:
            return decreasing_history(datetime.now() - timedelta(days=365))
        else:
            return []


class MockAsyncClient(AsyncMock):
    """Mock SENSiT client with options for different tank level/history data"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "tank_level" in kwargs:
            self._level = kwargs["tank_level"]
        else:
            self._level = MOCK_TANK_LEVEL
        if "history_type" in kwargs:
            self._history_type = kwargs["history_type"]
        else:
            self._history_type = HistoryType.DECREASING
        if "num_tanks" in kwargs and kwargs["num_tanks"] is not None:
            self._num_tanks = kwargs["num_tanks"]
        else:
            self._num_tanks = 1

    @async_property
    async def tanks(self):
        if self._num_tanks == 1:
            return [
                MockAsyncTank(tank_level=self._level, history_type=self._history_type)
            ]
        else:
            return [
                MockAsyncTank(
                    tank_level=self._level,
                    history_type=self._history_type,
                    tank_num=tank_num,
                )
                for tank_num in range(1, self._num_tanks + 1)
            ]


@pytest_asyncio.fixture(params=["tank_level", "history_type", "num_tanks"])
def mock_sensor_client(request):
    """Replace the AsyncSensorClient with a mock context manager"""
    num_tanks = None
    if type(request.param) == list and len(request.param) == 1:
        tank_level = request.param[0]
        history_type = HistoryType.DECREASING
    elif type(request.param) == list and len(request.param) == 2:
        tank_level = request.param[0]
        history_type = request.param[1]
    elif type(request.param) == list and len(request.param) == 3:
        tank_level = request.param[0]
        history_type = request.param[1]
        num_tanks = request.param[2]
    else:
        tank_level = MOCK_TANK_LEVEL
        history_type = HistoryType.DECREASING

    # AsyncSensorClient is instantiated in different import contexts
    # See https://docs.python.org/3/library/unittest.mock.html#where-to-patch
    with patch("connectsensor.AsyncSensorClient") as mock_client, patch(
        "custom_components.kingspan_watchman_sensit.api.AsyncSensorClient"
    ) as ha_mock_client:
        mock_client.return_value.__aenter__.return_value = MockAsyncClient(
            tank_level=tank_level, history_type=history_type, num_tanks=num_tanks
        )
        ha_mock_client.return_value.__aenter__.return_value = MockAsyncClient(
            tank_level=tank_level, history_type=history_type, num_tanks=num_tanks
        )
        yield
