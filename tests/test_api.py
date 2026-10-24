"""Tests for Kingspan Watchman SENSiT api."""

import asyncio
from datetime import datetime
from unittest.mock import patch

import httpx
import pandas as pd
import pytest
from connectsensor import KingspanAPIError
from connectsensor.client import APIVersion
from custom_components.kingspan_watchman_sensit.api import (
    SENSiTApiClient,
    SENSiTApiClientError,
    SENSiTConnectionError,
    TankData,
    filter_history,
)
from homeassistant.util.dt import as_local, set_default_time_zone
from httpx import TimeoutException as httpxTimeoutException
from tzlocal import get_localzone

from .conftest import MockAsyncClient
from .const import (
    MOCK_GET_DATA_METHOD,
    MOCK_TANK_CAPACITY,
    MOCK_TANK_LEVEL,
    MOCK_TANK_MODEL,
    MOCK_TANK_NAME,
    MOCK_TANK_SERIAL_NUMBER,
)

TEST_USERNAME = "test-user"
TEST_PASSWORD = "test-pwd"


async def test_api(mock_sensor_client, mocker, caplog):
    """Test API calls."""
    set_default_time_zone(get_localzone())

    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD, 14)
    tank_data = await api.async_get_data()
    assert tank_data[0].level == MOCK_TANK_LEVEL
    assert tank_data[0].serial_number == MOCK_TANK_SERIAL_NUMBER
    assert tank_data[0].model == MOCK_TANK_MODEL
    assert tank_data[0].name == MOCK_TANK_NAME
    assert tank_data[0].capacity == MOCK_TANK_CAPACITY
    history = pd.DataFrame(tank_data[0].history)
    assert tank_data[0].last_read == as_local(history.iloc[-1].reading_date)
    assert round(tank_data[0].usage_rate, 2) == 96.67
    assert tank_data[0].forecast_empty == 10


@pytest.mark.parametrize(
    ("side_effect", "expected_exception", "expected_msg"),
    [
        (
            asyncio.TimeoutError,
            SENSiTConnectionError,
            f"Timeout or connection error logging in for {TEST_USERNAME}: ",
        ),
        (
            KingspanAPIError,
            SENSiTApiClientError,
            f"API error logging in for {TEST_USERNAME}: unknown API error",
        ),
        (Exception, Exception, f"Unhandled error logging in for {TEST_USERNAME}"),
    ],
)
async def test_api_login_errors(mocker, side_effect, expected_exception, expected_msg):
    """Test API login error handling."""
    set_default_time_zone(get_localzone())

    mocker.patch("connectsensor.client.AsyncSensorClient.login", side_effect=side_effect)
    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD, 14)

    with pytest.raises(expected_exception) as exc:
        assert not await api.check_credentials()
    assert str(exc.value) == expected_msg


@pytest.mark.parametrize(
    ("usage_window", "expected_rate"),
    [
        (None, 96.67),  # Tests default fallback
        (5, 100.0),  # Tests explicitly shortened window
    ],
)
async def test_api_filtering(mock_sensor_client, usage_window, expected_rate):
    """Test API history filtering calculates usage correctly."""
    kwargs = {}
    if usage_window is not None:
        kwargs["usage_window"] = usage_window

    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD, **kwargs)
    tank_data = await api.async_get_data()
    assert round(tank_data[0].usage_rate, 2) == expected_rate


def test_api_no_history_zero_usage():
    """Exercise the no-history and zero-usage edge cases for coverage."""
    _ = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD)

    assert filter_history(None, 14) == []

    tank_data = TankData(
        history=[
            {
                "reading_date": datetime.now(),
                "level_litres": 100.0,
            }
        ]
    )
    assert tank_data.usage_rate == 0.0
    assert tank_data.forecast_empty == 0


@pytest.mark.parametrize(
    ("side_effect", "expected_msg"),
    [
        (asyncio.TimeoutError, f"Timeout or connection error fetching data for {TEST_USERNAME}: "),
        (
            httpxTimeoutException("HTTPX timeout error"),
            f"Timeout or connection error fetching data for {TEST_USERNAME}: HTTPX timeout error",
        ),
    ],
)
async def test_api_get_data_timeouts(mock_sensor_client, mocker, side_effect, expected_msg):
    """Test API data fetching timeout handling."""
    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD, 14)
    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=side_effect)

    with pytest.raises(SENSiTConnectionError) as exc:
        await api.async_get_data()
    assert str(exc.value) == expected_msg


async def test_api_debug_logging(caplog, mocker):
    """Test API debug can be enabled."""
    mocker.patch("connectsensor.client.AsyncSensorClient.login")
    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD, debug=True)
    _ = await api.check_credentials()

    assert "Init API with version=KNECT_V1" in caplog.text


async def test_api_client_injection(mocker):
    """Test that the injected httpx client is passed through to connectsensor."""
    mock_httpx = httpx.AsyncClient()
    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD, 14, client=mock_httpx)

    with patch("custom_components.kingspan_watchman_sensit.api.AsyncSensorClient") as mock_client:
        mock_client.return_value.__aenter__.return_value = MockAsyncClient()
        await api.async_get_data()

        mock_client.assert_called_with(version=APIVersion.KNECT_V1, client=mock_httpx)
