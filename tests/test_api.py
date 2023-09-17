"""Tests for Kingspan Watchman SENSiT api."""
import asyncio
import random
from datetime import datetime, timezone

import pandas as pd
import pytest
from connectsensor import APIError

from custom_components.kingspan_watchman_sensit.api import SENSiTApiClient

from .const import (
    MOCK_GET_DATA_METHOD,
    MOCK_TANK_CAPACITY,
    MOCK_TANK_LEVEL,
    MOCK_TANK_MODEL,
    MOCK_TANK_NAME,
    MOCK_TANK_SERIAL_NUMBER,
)


async def test_api(hass, mock_sensor_client, mocker, caplog):
    """Test API calls."""
    random.seed(999)

    api = SENSiTApiClient("test", "test", 14)
    tank_data = await api.async_get_data()
    assert tank_data[0].level == MOCK_TANK_LEVEL
    assert tank_data[0].serial_number == MOCK_TANK_SERIAL_NUMBER
    assert tank_data[0].model == MOCK_TANK_MODEL
    assert tank_data[0].name == MOCK_TANK_NAME
    assert tank_data[0].capacity == MOCK_TANK_CAPACITY
    history = pd.DataFrame(tank_data[0].history)
    print(history)
    local_tzinfo = datetime.now(timezone.utc).astimezone().tzinfo
    assert tank_data[0].last_read == history.iloc[-1].reading_date.replace(
        tzinfo=local_tzinfo
    )
    assert int(tank_data[0].usage_rate) == 100
    assert tank_data[0].forecast_empty == 10

    caplog.clear()
    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=asyncio.TimeoutError)
    _ = await api.async_get_data()
    assert len(caplog.record_tuples) == 1
    assert "Timeout error logging in" in caplog.record_tuples[0][2]

    caplog.clear()
    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=APIError("api-test error"))
    _ = await api.async_get_data()
    assert len(caplog.record_tuples) == 1
    assert "API error logging in as test: api-test" in caplog.record_tuples[0][2]

    caplog.clear()
    mocker.patch(MOCK_GET_DATA_METHOD, side_effect=Exception())
    _ = await api.async_get_data()
    assert len(caplog.record_tuples) == 1
    assert "Unhandled error" in caplog.record_tuples[0][2]


async def test_api_filtering(hass, mock_sensor_client, mocker):
    """Test API calls."""
    random.seed(999)

    api = SENSiTApiClient("test", "test", 10)
    tank_data = await api.async_get_data()
    history = pd.DataFrame(tank_data[0].history)
    assert int(tank_data[0].usage_rate) == 102

    api = SENSiTApiClient("test", "test", 5)
    tank_data = await api.async_get_data()
    history = pd.DataFrame(tank_data[0].history)
    assert int(tank_data[0].usage_rate) == 115
