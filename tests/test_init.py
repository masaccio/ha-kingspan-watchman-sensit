"""Test Kingspan Watchman SENSiT setup process."""

import logging
from unittest.mock import AsyncMock

import pytest
from connectsensor.exceptions import (
    KingspanAPIError,
    KingspanInvalidCredentialsError,
    KingspanTimeoutError,
)
from custom_components.kingspan_watchman_sensit import (
    SENSiTDataUpdateCoordinator,
)
from custom_components.kingspan_watchman_sensit.api import (
    SENSiTApiClientError,
    SENSiTConnectionError,
)
from custom_components.kingspan_watchman_sensit.const import DOMAIN
from custom_components.kingspan_watchman_sensit.diagnostics import (
    async_get_config_entry_diagnostics,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import MOCK_CONFIG, MOCK_TANK_LEVEL, HistoryType


async def test_setup_unload_and_reload_entry(hass, mock_sensor_client):
    """Test entry setup and unload state transitions."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED
    assert isinstance(config_entry.runtime_data, SENSiTDataUpdateCoordinator)

    # Reload the entry and assert it remains loaded
    await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state == ConfigEntryState.LOADED

    # Unload the entry via the core HA manager to properly alter the state
    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state == ConfigEntryState.NOT_LOADED


async def test_auth_missing(hass, mock_sensor_client):
    """Test entry setup and unload."""
    # Create a mock entry so we don't have to go through config flow
    config_entry = MockConfigEntry(domain=DOMAIN, data={"username": None}, entry_id="test")
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.SETUP_ERROR
    assert config_entry.entry_id not in hass.data.get(DOMAIN, {})
    assert config_entry.error_reason_translation_key == "credentials_not_set"
    assert DOMAIN not in hass.data


@pytest.mark.parametrize(
    (
        "mock_sensor_client",
        "log_level",
        "expected_state",
        "expected_log",
        "attr_name",
        "attr_value",
        "expect_repair_issue",
    ),
    [
        (
            {"exception": KingspanInvalidCredentialsError("test bad auth")},
            logging.ERROR,
            ConfigEntryState.SETUP_ERROR,
            "Invalid credentials for test@example.com: test bad auth",
            "error_reason_translation_key",
            "credentials_invalid",
            True,
        ),
        (
            {"exception": KingspanTimeoutError("test timeout")},
            logging.ERROR,
            ConfigEntryState.SETUP_RETRY,
            "Timeout or connection error fetching data for test@example.com: test timeout",
            "reason",
            "Timed out while connecting to the Kingspan service",
            False,
        ),
        (
            {"exception": KingspanAPIError("no level data")},
            logging.WARNING,
            ConfigEntryState.SETUP_ERROR,
            "No data available for username 'test@example.com",
            None,
            None,
            False,
        ),
    ],
    indirect=["mock_sensor_client"],
)
async def test_setup_auth_failures(  # noqa: PLR0913, PLR0917
    hass,
    mock_sensor_client,
    caplog,
    log_level,
    expected_state,
    expected_log,
    attr_name,
    attr_value,
    expect_repair_issue,
):
    """Test entry setup handles authentication and connection failures cleanly."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    config_entry.add_to_hass(hass)

    with caplog.at_level(log_level):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == expected_state
    assert config_entry.entry_id not in hass.data.get(DOMAIN, {})
    assert expected_log in caplog.text

    if attr_name:
        assert getattr(config_entry, attr_name) == attr_value

    if expect_repair_issue:
        issue_registry = ir.async_get(hass)
        issue = issue_registry.async_get_issue(DOMAIN, f"credentials_{config_entry.entry_id}")
        assert issue is not None
        assert issue.is_fixable is True


@pytest.mark.parametrize("mock_sensor_client", [{"num_tanks": 0}], indirect=True)
async def test_setup_entry_no_data_return_false(hass, mock_sensor_client):
    """Test setup exits cleanly when a valid login finds an empty tank list."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.SETUP_ERROR
    assert config_entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_runtime_data_fallback_and_unload(hass, mock_sensor_client):
    """Runtime data should be stored on the entry and cleaned up on unload."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diagnostics["tank_count"] == 1
    assert config_entry.runtime_data is not None

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.entry_id not in hass.data.get(DOMAIN, {})


@pytest.mark.parametrize(
    "exception",
    [
        SENSiTApiClientError("api-test error"),
        SENSiTConnectionError("connection timeout"),
    ],
)
async def test_coordinator_logs_available_again(
    hass, mock_sensor_client, mocker, caplog, exception
):
    """Coordinator should log a recovery message after a previously failed refresh."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data
    caplog.set_level(logging.INFO)
    caplog.clear()

    mocker.patch.object(
        coordinator.api,
        "async_get_data",
        AsyncMock(side_effect=exception),
    )

    # Trigger twice to check it's logged just once
    with pytest.raises(Exception):  # noqa: B017
        await coordinator._async_update_data()
    with pytest.raises(Exception):  # noqa: B017
        await coordinator._async_update_data()

    warnings = [
        record
        for record in caplog.records
        if "Error communicating with Kingspan API" in record.message
    ]
    assert len(warnings) == 1
    assert coordinator._unavailable_logged is True

    # Restore the working response
    mocker.patch.object(
        coordinator.api,
        "async_get_data",
        AsyncMock(return_value=coordinator.data),
    )
    await coordinator._async_update_data()

    assert "Kingspan service is available again" in caplog.text
    assert coordinator._unavailable_logged is False


@pytest.mark.parametrize(
    "mock_sensor_client",
    [{"tank_level": MOCK_TANK_LEVEL, "history_type": HistoryType.DECREASING, "num_tanks": 2}],
    indirect=True,
)
async def test_diagnostics(hass, mock_sensor_client):
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["config_entry_data"]["username"] == "**REDACTED**"
    assert diagnostics["config_entry_data"]["password"] == "**REDACTED**"
    assert diagnostics["tank_count"] == 2
    assert len(diagnostics["tanks"]) == 2
    assert diagnostics["last_update_success"]
    assert diagnostics["tanks"][0]["serial_number"] == "**REDACTED**"
    assert diagnostics["tanks"][0]["level"] == 1000
