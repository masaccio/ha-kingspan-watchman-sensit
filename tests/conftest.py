"""Global fixtures for kingspan_connect integration."""

import pytest

from async_property import async_property
from unittest.mock import patch, AsyncMock
from connectsensor import APIError

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture enables loading custom integrations in all tests.
# Remove to enable selective use of this fixture
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
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
    async def level(self):
        return 1000


class MockAsyncClient(AsyncMock):
    @async_property
    async def tanks(self):
        return [MockAsyncTank()]


@pytest.fixture(name="mock_sensor_client")
def mock_sensor_client_fixture():
    """Replace the AsyncSensorClient with a mock context manager"""
    with patch("connectsensor.AsyncSensorClient") as mock_client, patch(
        "custom_components.kingspan_connect.AsyncSensorClient"
    ) as ha_mock_client:
        mock_client.return_value.__aenter__.return_value = MockAsyncClient()
        ha_mock_client.return_value.__aenter__.return_value = MockAsyncClient()
        yield
