"""Tests for Kingspan Watchman SENSiT api."""

import asyncio
from datetime import datetime

import pandas as pd
import pytest
from connectsensor import KingspanAPIError
from custom_components.kingspan_watchman_sensit.api import (
    SENSiTApiClient,
    SENSiTAuthError,
    SENSiTConnectionError,
    TankData,
    filter_history,
)
from homeassistant.util.dt import as_local, set_default_time_zone
from httpx import TimeoutException as httpxTimeoutException
from tzlocal import get_localzone

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

    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=asyncio.TimeoutError)
    with pytest.raises(SENSiTConnectionError) as exc:
        _ = await api.async_get_data()
    assert str(exc.value) == f"Timeout or connection error fetching data for {TEST_USERNAME}"


async def test_api_timeout(mocker):
    """Test API calls."""
    set_default_time_zone(get_localzone())

    mocker.patch("connectsensor.client.AsyncSensorClient.login", side_effect=asyncio.TimeoutError)
    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD, 14)

    with pytest.raises(SENSiTConnectionError) as exc:
        assert not await api.check_credentials()
    assert str(exc.value) == f"Timeout logging in as {TEST_USERNAME}"


async def test_api_error(mocker):
    """Test API calls."""
    set_default_time_zone(get_localzone())

    mocker.patch("connectsensor.client.AsyncSensorClient.login", side_effect=KingspanAPIError)
    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD, 14)

    with pytest.raises(SENSiTAuthError) as exc:
        assert not await api.check_credentials()
    assert str(exc.value) == f"API error logging in as {TEST_USERNAME}"


async def test_api_generic_error(mocker):
    """Test API calls."""
    set_default_time_zone(get_localzone())

    mocker.patch("connectsensor.client.AsyncSensorClient.login", side_effect=Exception)
    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD, 14)
    with pytest.raises(Exception) as exc:  # noqa: B017
        assert not await api.check_credentials()
    assert str(exc.value) == f"Unhandled error logging in as {TEST_USERNAME}"


async def test_api_filtering(mock_sensor_client):
    """Test API calls."""
    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD)
    tank_data = await api.async_get_data()
    assert round(tank_data[0].usage_rate, 2) == 96.67

    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD, 5)
    tank_data = await api.async_get_data()
    assert int(tank_data[0].usage_rate) == 100.0


def test_api_no_history_zero_usage():
    """Exercise the no-history and zero-usage edge cases for coverage."""
    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD)

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


@pytest.mark.asyncio
async def test_async_httpx_timeout(mocker, mock_sensor_client):
    api = SENSiTApiClient(TEST_USERNAME, TEST_PASSWORD)
    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=httpxTimeoutException("HTTPX timeout error"))

    with pytest.raises(SENSiTConnectionError) as exc:
        await api.async_get_data()
    assert str(exc.value) == f"Timeout or connection error fetching data for {TEST_USERNAME}"


async def zeep_exception(*args, **kwargs):
    raise httpxTimeoutException("Test error")
