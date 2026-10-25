"""Global fixtures for Kingspan Watchman SENSiT integration."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from async_property import async_property
from connectsensor.exceptions import KingspanAPIError

from .const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    MOCK_CONFIG,
    MOCK_TANK_CAPACITY,
    MOCK_TANK_LEVEL,
    MOCK_TANK_MODEL,
    MOCK_TANK_NAME,
    MOCK_TANK_SERIAL_NUMBER,
    HistoryType,
)

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture enables loading custom integrations in all tests.
@pytest_asyncio.fixture(autouse=True)  # pyright: ignore[reportArgumentType]
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest_asyncio.fixture(autouse=True)  # pyright: ignore[reportArgumentType]
def clear_proxy_env(monkeypatch):
    """Ensure tests do not inherit proxy settings from the host environment."""
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "NO_PROXY",
        "no_proxy",
    ):
        monkeypatch.delenv(key, raising=False)
    yield


@pytest_asyncio.fixture(name="mock_password_check")  # pyright: ignore[reportArgumentType]
def mock_password_check_fixture():
    """Check password and return True or raise a KingspanAPIError if invalid"""

    def mock_check_credentials(self):
        if (
            self._username != MOCK_CONFIG[CONF_USERNAME]
            or self._password != MOCK_CONFIG[CONF_PASSWORD]
        ):
            raise KingspanAPIError()
        return True

    with patch(
        "custom_components.kingspan_watchman_sensit.SENSiTApiClient.check_credentials",
        side_effect=mock_check_credentials,
    ):
        yield


def _decreasing_history(start_date: datetime) -> list[dict]:
    history = []
    start_date = start_date.replace(hour=0, minute=30, second=0, microsecond=0) - timedelta(days=30)

    for day in range(1, 20):
        percent = 100 - (day * 4)
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
        percent = 100 - ((day - 20) * 5)
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
    async def last_read(self) -> datetime:
        history = await self.history()
        if len(history) > 0:
            return history[-1]["reading_date"]
        else:
            return datetime.now()

    async def history(self) -> list[dict]:
        # Build a month of history with a refill halfway through
        if self._history_type == HistoryType.DECREASING:
            return _decreasing_history(datetime.now())
        elif self._history_type == HistoryType.EXPIRED:
            return _decreasing_history(datetime.now() - timedelta(days=365))
        else:
            return []


class MockAsyncClient(AsyncMock):
    """Mock SENSiT client with options for different tank level/history data"""

    def __init__(self, *args, **kwargs):
        injected_client = kwargs.pop("client", None)

        super().__init__(*args, **kwargs)

        self._injected_client = injected_client
        self._level = kwargs.get("tank_level", MOCK_TANK_LEVEL)
        self._history_type = kwargs.get("history_type", HistoryType.DECREASING)
        self._num_tanks = kwargs.get("num_tanks", 1)
        self._exception = kwargs.get("exception", None)

    @async_property
    async def tanks(self):
        if self._num_tanks == 1:
            return [MockAsyncTank(tank_level=self._level, history_type=self._history_type)]
        else:
            return [
                MockAsyncTank(
                    tank_level=self._level,
                    history_type=self._history_type,
                    tank_num=tank_num,
                )
                for tank_num in range(1, self._num_tanks + 1)
            ]

    async def login(self, username: str, password: str) -> None:
        if self._exception:
            raise (self._exception)


@pytest_asyncio.fixture(name="mock_sensor_client")  # pyright: ignore[reportArgumentType]
def mock_sensor_client(request):
    """Replace the AsyncSensorClient with a mock context manager"""
    params = getattr(request, "param", {})
    tank_level = params.get("tank_level", MOCK_TANK_LEVEL)
    history_type = params.get("history_type", HistoryType.DECREASING)
    num_tanks = params.get("num_tanks", 1)
    exception = params.get("exception", None)

    # AsyncSensorClient is instantiated in different import contexts
    # See https://docs.python.org/3/library/unittest.mock.html#where-to-patch
    with (
        patch("connectsensor.client.AsyncSensorClient") as mock_client,
        patch("custom_components.kingspan_watchman_sensit.api.AsyncSensorClient") as ha_mock_client,
    ):
        mock_client.return_value.__aenter__.return_value = MockAsyncClient(
            tank_level=tank_level,
            history_type=history_type,
            num_tanks=num_tanks,
            exception=exception,
        )
        ha_mock_client.return_value.__aenter__.return_value = MockAsyncClient(
            tank_level=tank_level,
            history_type=history_type,
            num_tanks=num_tanks,
            exception=exception,
        )
        yield
