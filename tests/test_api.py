"""Tests for Kingspan Watchman SENSiT api."""

import asyncio
import logging

import pandas as pd
import pytest
from connectsensor import APIError
from custom_components.kingspan_watchman_sensit.api import SENSiTApiClient
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


async def test_api(mock_sensor_client, mocker, caplog):
    """Test API calls."""
    set_default_time_zone(get_localzone())

    api = SENSiTApiClient("test", "test", 14)
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
    with pytest.raises(APIError) as e:
        _ = await api.async_get_data()
    assert "Timeout error" in str(e)


async def test_api_timeout(mocker, caplog):
    """Test API calls."""
    set_default_time_zone(get_localzone())

    mocker.patch("connectsensor.client.AsyncSensorClient.login", side_effect=asyncio.TimeoutError)
    api = SENSiTApiClient("test", "test", 14)
    caplog.clear()

    assert not await api.check_credentials()
    assert "Timeout error logging in" in caplog.text


async def test_api_error(mocker, caplog):
    """Test API calls."""
    set_default_time_zone(get_localzone())

    mocker.patch("connectsensor.client.AsyncSensorClient.login", side_effect=APIError)
    api = SENSiTApiClient("test", "test", 14)
    caplog.clear()

    assert not await api.check_credentials()
    assert "API error logging in" in caplog.text


async def test_api_generic_error(mocker, caplog):
    """Test API calls."""
    set_default_time_zone(get_localzone())

    mocker.patch("connectsensor.client.AsyncSensorClient.login", side_effect=Exception)
    api = SENSiTApiClient("test", "test", 14)
    caplog.clear()

    assert not await api.check_credentials()
    assert "Unhandled error logging in" in caplog.text


async def test_api_filtering(mock_sensor_client):
    """Test API calls."""
    api = SENSiTApiClient("test", "test")
    tank_data = await api.async_get_data()
    assert round(tank_data[0].usage_rate, 2) == 96.67

    api = SENSiTApiClient("test", "test", 5)
    tank_data = await api.async_get_data()
    assert int(tank_data[0].usage_rate) == 100.0


@pytest.mark.asyncio
async def test_async_httpx_timeout(mocker, mock_sensor_client, caplog):
    api = SENSiTApiClient("test", "test")
    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=httpxTimeoutException("HTTPX timeout error"))

    caplog.clear()
    with pytest.raises(APIError) as exc:
        await api.async_get_data()
    assert "HTTPX timeout error fetching data" in caplog.text
    assert "HTTPX timeout error fetching data" in str(exc.value)


async def zeep_exception(*args, **kwargs):
    raise httpxTimeoutException("Test error")


@pytest.mark.asyncio
async def test_async_httpx_exception(mocker, caplog):
    mocker.patch(
        "connectsensor.client.AsyncSensorClient._init_zeep",
        side_effect=httpxTimeoutException("Test error"),
    )

    api = SENSiTApiClient("test", "test")
    caplog.clear()
    caplog.set_level(logging.ERROR)
    assert not await api.check_credentials()
    assert "HTTPX timeout error logging in" in caplog.text
