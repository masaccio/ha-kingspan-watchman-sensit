"""Tests for Watchman SENSiT api."""
import asyncio
import pytest

from custom_components.kingspan_watchman_sensit.api import SENSiTApiClient
from connectsensor import APIError

from .const import (
    MOCK_GET_DATA_METHOD,
    MOCK_TANK_LEVEL,
    MOCK_TANK_SERIAL_NUMBER,
    MOCK_TANK_MODEL,
    MOCK_TANK_NAME,
    MOCK_TANK_CAPACITY,
    MOCK_TANK_LAST_READ,
)


@pytest.mark.asyncio
async def test_api(hass, mock_sensor_client, mocker, caplog):
    """Test API calls."""
    api = SENSiTApiClient("test", "test")
    tank_data = await api.async_get_data()
    assert tank_data.level == MOCK_TANK_LEVEL
    assert tank_data.serial_number == MOCK_TANK_SERIAL_NUMBER
    assert tank_data.model == MOCK_TANK_MODEL
    assert tank_data.name == MOCK_TANK_NAME
    assert tank_data.capacity == MOCK_TANK_CAPACITY
    assert tank_data.last_read == MOCK_TANK_LAST_READ

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
