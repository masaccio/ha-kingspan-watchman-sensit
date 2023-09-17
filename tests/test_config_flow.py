"""Test Kingspan Watchman SENSiT config flow."""
from unittest.mock import patch

import pytest
import pytest_asyncio
from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kingspan_watchman_sensit.const import DOMAIN

from .const import MOCK_CONFIG, CONF_PASSWORD


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
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    # If a user were to enter `test_username` for username and `test_password`
    # for password, it would result in this function call
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )

    # Check that the config flow is complete and a new entry is created with
    # the input data
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "test@example.com"
    assert result["data"] == MOCK_CONFIG
    assert result["result"]


async def test_failed_config_flow(hass, error_on_get_data):
    """Test a failed config flow due to credential validation failure."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {"base": "auth"}


async def test_options_flow(hass):
    """Test an options flow."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Verify that the first options step is a user form
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"update_interval": 2, "usage_window": 10}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "Mock Title"

    assert entry.options == {"update_interval": 2, "usage_window": 10}


# Re-auth test Copyright (c) 2020 Joakim Sørensen @ludeeus
async def test_reauth_config_flow(hass, bypass_get_data):
    """Test a successful config flow."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    entry.add_to_hass(hass)

    # Initialize a config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_REAUTH}
    )

    # Check that the config flow shows the reauth form as the first step
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "reauth_confirm"

    # If a user were to confirm the re-auth start, this function call
    result_2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    # It should load the user form
    assert result_2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_2["step_id"] == "user"

    updated_config = MOCK_CONFIG
    updated_config[CONF_PASSWORD] = "NewH8x0rP455!"

    # If a user entered a new password, this would happen
    result_3 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=updated_config
    )

    # Check that the config flow is complete and a new entry is created with
    # the input data
    assert result_3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result_3["title"] == "test@example.com"
    assert result_3["data"] == MOCK_CONFIG
    assert result_3["result"]
