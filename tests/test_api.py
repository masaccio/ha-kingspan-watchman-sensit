"""Tests for Kingspan Watchman SENSiT api."""

import asyncio
from datetime import datetime, timezone

import pandas as pd
import pytest
from connectsensor.exceptions import APIError
from custom_components.kingspan_watchman_sensit.api import SENSiTApiClient

from .const import (
    MOCK_GET_DATA_METHOD,
    MOCK_TANK_CAPACITY,
    MOCK_TANK_LEVEL,
    MOCK_TANK_MODEL,
    MOCK_TANK_NAME,
    MOCK_TANK_SERIAL_NUMBER,
)


async def test_api(mock_sensor_client, mocker):
    """Test API calls."""
    api = SENSiTApiClient("test", "test", 14)
    tank_data = await api.async_get_data()
    assert tank_data[0].level == MOCK_TANK_LEVEL
    assert tank_data[0].serial_number == MOCK_TANK_SERIAL_NUMBER
    assert tank_data[0].model == MOCK_TANK_MODEL
    assert tank_data[0].name == MOCK_TANK_NAME
    assert tank_data[0].capacity == MOCK_TANK_CAPACITY
    history = pd.DataFrame(tank_data[0].history)
    local_tzinfo = datetime.now(timezone.utc).astimezone().tzinfo
    assert tank_data[0].last_read == history.iloc[-1].reading_date.replace(tzinfo=local_tzinfo)
    assert round(tank_data[0].usage_rate, 2) == 96.67
    assert tank_data[0].forecast_empty == 10

    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=asyncio.TimeoutError)
    with pytest.raises(APIError) as e:
        _ = await api.async_get_data()
    assert "Timeout error logging in" in str(e)


async def test_api_filtering(mock_sensor_client):
    """Test API calls."""
    api = SENSiTApiClient("test", "test")
    tank_data = await api.async_get_data()
    assert round(tank_data[0].usage_rate, 2) == 96.67

    api = SENSiTApiClient("test", "test", 5)
    tank_data = await api.async_get_data()
    assert int(tank_data[0].usage_rate) == 100.0
