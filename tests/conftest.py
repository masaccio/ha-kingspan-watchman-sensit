"""Global fixtures for kingspan_connect integration."""
# Fixtures allow you to replace functions with a Mock object. You can perform
# many options via the Mock to reflect a particular behavior from the original
# function that you want to see without going through the function's actual logic.
# Fixtures can either be passed into tests as parameters, or if autouse=True, they
# will automatically be used across all tests.
#
# Fixtures that are defined in conftest.py are available across all tests. You can also
# define fixtures within a particular test file to scope them locally.
#
# pytest_homeassistant_custom_component provides some fixtures that are provided by
# Home Assistant core. You can find those fixture definitions here:
# https://github.com/MatthewFlamm/pytest-homeassistant-custom-component/blob/master/pytest_homeassistant_custom_component/common.py
#
# See here for more info: https://docs.pytest.org/en/latest/fixture.html (note that
# pytest includes fixtures OOB which you can use as defined on this page)
from unittest.mock import patch, AsyncMock
from connectsensor import APIError
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture enables loading custom integrations in all tests.
# Remove to enable selective use of this fixture
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


# In this fixture, we are forcing calls to async_get_data to raise an Exception. This is useful
# for exception handling.
@pytest.fixture(name="error_sensor_client")
def error_sensor_client_fixture():
    """Throw an exception from a mock AsyncSensorClient"""
    with patch(
        "connectsensor.AsyncSensorClient",
        # side_effect=Exception,
    ) as mock_client:
        mock_client.return_value.__aenter__.side_effect = APIError
        yield


@pytest.fixture(name="mock_sensor_client")
def mock_sensor_client_fixture():
    """Replace the AsyncSensorClient with a mock context manager"""
    with patch("connectsensor.AsyncSensorClient") as mock_client:
        mock_client.return_value.__aenter__.return_value = AsyncMock()
        yield
