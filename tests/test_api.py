"""Tests for Watchman SENSiT api."""
import pytest

from custom_components.kingspan_watchman_sensit.api import SENSiTApiClient

from .const import (
    MOCK_TANK_LEVEL,
    MOCK_TANK_SERIAL_NUMBER,
    MOCK_TANK_MODEL,
    MOCK_TANK_NAME,
    MOCK_TANK_CAPACITY,
    MOCK_TANK_LAST_READ,
)


@pytest.mark.asyncio
async def test_api(hass, mock_sensor_client, caplog):
    """Test API calls."""
    api = SENSiTApiClient("test", "test")
    tank_data = await api.async_get_data()
    assert tank_data.level == MOCK_TANK_LEVEL
    assert tank_data.serial_number == MOCK_TANK_SERIAL_NUMBER
    assert tank_data.model == MOCK_TANK_MODEL
    assert tank_data.name == MOCK_TANK_NAME
    assert tank_data.capacity == MOCK_TANK_CAPACITY
    assert tank_data.last_read == MOCK_TANK_LAST_READ

    # We do the same for `async_set_title`. Note the difference in the mock call
    # between the previous step and this one. We use `patch` here instead of `get`
    # because we know that `async_set_title` calls `api_wrapper` with `patch` as the
    # first parameter
    # aioclient_mock.patch("https://jsonplaceholder.typicode.com/posts/1")
    # mocker.patch(MOCK_GET_DATA_METHOD)
    # assert await api.async_set_title("test") is None

    # # In order to get 100% coverage, we need to test `api_wrapper` to test the code
    # # that isn't already called by `async_get_data` and `async_set_title`. Because the
    # # only logic that lives inside `api_wrapper` that is not being handled by a third
    # # party library (aiohttp) is the exception handling, we also want to simulate
    # # raising the exceptions to ensure that the function handles them as expected.
    # # The caplog fixture allows access to log messages in tests. This is particularly
    # # useful during exception handling testing since often the only action as part of
    # # exception handling is a logging statement
    # caplog.clear()
    # mocker.patch(MOCK_GET_DATA_METHOD)
    # aioclient_mock.put(
    #     "https://jsonplaceholder.typicode.com/posts/1", exc=asyncio.TimeoutError
    # )
    # assert (
    #     await api.api_wrapper("put", "https://jsonplaceholder.typicode.com/posts/1")
    #     is None
    # )
    # assert (
    #     len(caplog.record_tuples) == 1
    #     and "Timeout error fetching information from" in caplog.record_tuples[0][2]
    # )

    # caplog.clear()
    # aioclient_mock.post(
    #     "https://jsonplaceholder.typicode.com/posts/1", exc=aiohttp.ClientError
    # )
    # assert (
    #     await api.api_wrapper("post", "https://jsonplaceholder.typicode.com/posts/1")
    #     is None
    # )
    # assert (
    #     len(caplog.record_tuples) == 1
    #     and "Error fetching information from" in caplog.record_tuples[0][2]
    # )

    # caplog.clear()
    # aioclient_mock.post("https://jsonplaceholder.typicode.com/posts/2", exc=Exception)
    # assert (
    #     await api.api_wrapper("post", "https://jsonplaceholder.typicode.com/posts/2")
    #     is None
    # )
    # assert (
    #     len(caplog.record_tuples) == 1
    #     and "Something really wrong happened!" in caplog.record_tuples[0][2]
    # )

    # caplog.clear()
    # aioclient_mock.post("https://jsonplaceholder.typicode.com/posts/3", exc=TypeError)
    # assert (
    #     await api.api_wrapper("post", "https://jsonplaceholder.typicode.com/posts/3")
    #     is None
    # )
    # assert (
    #     len(caplog.record_tuples) == 1
    #     and "Error parsing information from" in caplog.record_tuples[0][2]
    # )
