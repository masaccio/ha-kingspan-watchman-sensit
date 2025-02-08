"""Test Kingspan Watchman SENSiT config flow."""

from logging import WARNING
from unittest.mock import patch

import pytest_asyncio
from custom_components.kingspan_watchman_sensit import async_setup_entry
from custom_components.kingspan_watchman_sensit.const import DOMAIN
from homeassistant import config_entries, data_entry_flow
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import MOCK_CONFIG


# This fixture bypasses the actual setup of the integration
# since we only want to test the config flow. We test the
# actual functionality of the integration in other test modules.
@pytest_asyncio.fixture(autouse=True)
def bypass_setup_fixture():
    """Prevent setup."""
    with patch(
        "custom_components.kingspan_watchman_sensit.async_setup",
        return_value=True,
    ), patch(
        "custom_components.kingspan_watchman_sensit.async_setup_entry",
        return_value=True,
    ):
        yield


async def test_successful_config_flow(hass, bypass_get_data):
    """Test a successful config flow."""
    # Initialize a config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Check that the config flow shows the user form as the first step
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )

    # Check that the config flow is complete and a new entry is created with
    # the input data
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "test@example.com"
    assert result["data"] == MOCK_CONFIG
    assert result["result"]


async def test_failed_config_flow(hass, error_on_get_data):
    """Test a failed config flow due to credential validation failure."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}


async def test_options_default_flow(hass, caplog):
    """Test an options flow."""
    caplog.clear()
    caplog.set_level(WARNING)

    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Mock Title"

    assert config_entry.options == {
        "debug_kingspan": False,
        "update_interval": 8,
        "usage_window": 14,
    }


async def test_options_flow(hass, bypass_get_data):
    """Test an options flow."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"debug_kingspan": True, "update_interval": 4, "usage_window": 28},
    )

    assert await async_setup_entry(hass, config_entry)

    assert config_entry.options == {
        "debug_kingspan": True,
        "update_interval": 4,
        "usage_window": 28,
    }

    hass.config_entries.async_update_entry(
        config_entry, options={"debug_kingspan": False, "update_interval": 8, "usage_window": 14}
    )
    await hass.async_block_till_done()

    assert config_entry.options == {
        "debug_kingspan": False,
        "update_interval": 8,
        "usage_window": 14,
    }


async def test_reauth_flow(hass, mock_password_check):
    """Test an reauthentication flow."""

    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    config_entry.async_start_reauth(hass)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["step_id"] == "reauth_confirm"

    _ = await hass.config_entries.flow.async_configure(flows[0]["flow_id"], user_input=MOCK_CONFIG)
    config_entry.async_start_reauth(hass)
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()

    assert flows[0]["context"]["source"] == "reauth"

    await hass.async_block_till_done()
