"""Global fixtures for Kingspan Watchman SENSiT integration."""
import pytest

from async_property import async_property
from unittest.mock import patch, AsyncMock
from connectsensor import APIError

from .const import (
    MOCK_TANK_LEVEL,
    MOCK_TANK_SERIAL_NUMBER,
    MOCK_TANK_MODEL,
    MOCK_TANK_NAME,
    MOCK_TANK_CAPACITY,
    MOCK_TANK_LAST_READ,
)

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture enables loading custom integrations in all tests.
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


# This fixture is used to prevent HomeAssistant from attempting to create and
# dismiss persistent notifications. These calls would fail without this fixture
# since the persistent_notification integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


# This fixture, when used, will result in calls to async_get_data to return None. To have the call
# return a value, we would add the `return_value=<VALUE_TO_RETURN>` parameter to the patch call.
@pytest.fixture(name="bypass_get_data")
def bypass_get_data_fixture():
    """Skip calls to get data from API."""
    with patch(
        "custom_components.kingspan_watchman_sensit.SENSiTApiClient.async_get_data"
    ):
        yield


# In this fixture, we are forcing calls to async_get_data to raise an Exception. This is useful
# for exception handling.
@pytest.fixture(name="error_on_get_data")
def error_get_data_fixture():
    """Simulate error when retrieving data from API."""
    with patch(
        "custom_components.kingspan_watchman_sensit.SENSiTApiClient.async_get_data",
        side_effect=Exception,
    ):
        yield


# AsyncSensorClient is instantiated in different import contexts
# See https://docs.python.org/3/library/unittest.mock.html#where-to-patch


@pytest.fixture(name="error_sensor_client")
def error_sensor_client_fixture():
    """Throw an exception from a mock AsyncSensorClient"""
    with patch("connectsensor.AsyncSensorClient",) as mock_client, patch(
        "custom_components.kingspan_connect.AsyncSensorClient"
    ) as ha_mock_client:
        mock_client.return_value.__aenter__.side_effect = APIError
        ha_mock_client.return_value.__aenter__.side_effect = APIError
        yield


class MockAsyncTank:
    def __init__(self, *args):
        pass

    @async_property
    async def level(self) -> int:
        return MOCK_TANK_LEVEL

    @async_property
    async def serial_number(self) -> str:
        return MOCK_TANK_SERIAL_NUMBER

    @async_property
    async def model(self) -> str:
        return MOCK_TANK_MODEL

    @async_property
    async def name(self) -> str:
        return MOCK_TANK_NAME

    @async_property
    async def capacity(self) -> int:
        return MOCK_TANK_CAPACITY

    @async_property
    async def last_read(self) -> str:
        return MOCK_TANK_LAST_READ


class MockAsyncClient(AsyncMock):
    @async_property
    async def tanks(self):
        return [MockAsyncTank()]


@pytest.fixture(name="mock_sensor_client")
def mock_sensor_client_fixture():
    """Replace the AsyncSensorClient with a mock context manager"""
    with patch("connectsensor.AsyncSensorClient") as mock_client, patch(
        "custom_components.kingspan_watchman_sensit.api.AsyncSensorClient"
        # "custom_components.kingspan_watchman_sensit.SENSiTApiClient.async_get_data.AsyncSensorClient"
    ) as ha_mock_client:
        mock_client.return_value.__aenter__.return_value = MockAsyncClient()
        ha_mock_client.return_value.__aenter__.return_value = MockAsyncClient()
        yield
