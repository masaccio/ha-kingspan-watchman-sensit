"""Test Kingspan Watchman SENSiT config flow."""

from unittest.mock import patch

import pytest
import pytest_asyncio
from connectsensor.exceptions import (
    KingspanAPIError,
    KingspanInvalidCredentialsError,
    KingspanTimeoutError,
)
from custom_components.kingspan_watchman_sensit.api import SENSiTAuthError
from custom_components.kingspan_watchman_sensit.config_flow import SENSiTFlowHandler
from custom_components.kingspan_watchman_sensit.const import (
    CONF_PASSWORD,
    DEFAULT_OIL_ENERGY_DENSITY,
    DOMAIN,
)
from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import CONF_NAME, CONF_USERNAME, MOCK_CONFIG


# This fixture bypasses the actual setup of the integration
# since we only want to test the config flow. We test the
# actual functionality of the integration in other test modules.
@pytest_asyncio.fixture(autouse=True)  # pyright: ignore[reportArgumentType]
def bypass_setup_fixture():
    """Prevent setup."""
    with (
        patch(
            "custom_components.kingspan_watchman_sensit.async_setup",
            return_value=True,
        ),
        patch(
            "custom_components.kingspan_watchman_sensit.async_setup_entry",
            return_value=True,
        ),
    ):
        yield


async def test_successful_config_flow(hass, mock_sensor_client):
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


def test_flow_matching_is_never_true():
    """The flow helper should report no match for unrelated flows."""
    flow = SENSiTFlowHandler()

    assert not flow.is_matching(object())
    assert not flow.is_matching(SENSiTFlowHandler())


@pytest.mark.parametrize(
    ("mock_sensor_client", "expected_error"),
    [
        ({"exception": KingspanInvalidCredentialsError("test bad auth")}, "auth"),
        ({"exception": KingspanTimeoutError("timeout")}, "cannot_connect"),
        ({"exception": KingspanAPIError("no level data")}, "no_data"),
        ({"exception": Exception("unknown")}, "unknown_error"),
    ],
    indirect=["mock_sensor_client"],
)
async def test_failed_config_flow(hass, mock_sensor_client, expected_error):
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
    assert result["errors"] == {"base": expected_error}


async def test_duplicate_config_flow_aborts(hass, mock_sensor_client):
    """A second config flow for the same username should abort as already configured."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id=MOCK_CONFIG["username"].casefold(),
    )
    existing_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("initial_options", "user_input", "expected_options"),
    [
        # 1. Default flow (empty input applies default options)
        (
            {},
            {},
            {
                "debug_kingspan": False,
                "oil_energy_density": DEFAULT_OIL_ENERGY_DENSITY,
                "update_interval": 8,
                "usage_window": 14,
            },
        ),
        # 2. Custom input flow
        (
            {},
            {"debug_kingspan": True, "update_interval": 4, "usage_window": 28},
            {
                "debug_kingspan": True,
                "oil_energy_density": DEFAULT_OIL_ENERGY_DENSITY,
                "update_interval": 4,
                "usage_window": 28,
            },
        ),
        # 3. Existing options overridden by new input
        (
            {
                "debug_kingspan": True,
                "update_interval": 4,
                "usage_window": 28,
                "oil_energy_density": 10.2,
            },
            {
                "debug_kingspan": False,
                "update_interval": 8,
                "usage_window": 14,
                "oil_energy_density": 10.5,
            },
            {
                "debug_kingspan": False,
                "oil_energy_density": 10.5,
                "update_interval": 8,
                "usage_window": 14,
            },
        ),
    ],
)
async def test_options_flows(
    hass, mock_sensor_client, initial_options, user_input, expected_options
):
    """Test options flows with varying initial states and user inputs."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, options=initial_options, entry_id="test"
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result1 = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result1["type"] == data_entry_flow.FlowResultType.FORM
    assert result1["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result1["flow_id"],
        user_input=user_input,
    )

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert config_entry.options == expected_options


@pytest.mark.parametrize(
    ("flow_source", "step_id", "success_reason", "pass_data"),
    [
        (config_entries.SOURCE_RECONFIGURE, "reconfigure", "reconfigure_successful", False),
        (config_entries.SOURCE_REAUTH, "reauth_confirm", "reauth_successful", True),
    ],
)
async def test_credential_update_success(  # noqa: PLR0913, PLR0917
    hass, mock_sensor_client, flow_source, step_id, success_reason, pass_data
):
    """Test reauth and reconfigure flows successfully update the password and abort."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, entry_id="test", unique_id=MOCK_CONFIG[CONF_USERNAME]
    )
    config_entry.add_to_hass(hass)

    kwargs = {"context": {"source": flow_source, "entry_id": config_entry.entry_id}}
    if pass_data:
        kwargs["data"] = config_entry.data

    result1 = await hass.config_entries.flow.async_init(DOMAIN, **kwargs)
    assert result1["type"] == data_entry_flow.FlowResultType.FORM
    assert result1["step_id"] == step_id

    result2 = await hass.config_entries.flow.async_configure(
        result1["flow_id"],
        user_input={
            CONF_USERNAME: MOCK_CONFIG[CONF_USERNAME],
            CONF_PASSWORD: "new-password",
            CONF_NAME: MOCK_CONFIG[CONF_NAME],
        },
    )

    assert result2["type"] == data_entry_flow.FlowResultType.ABORT
    assert result2["reason"] == success_reason
    assert config_entry.data[CONF_PASSWORD] == "new-password"


@pytest.mark.parametrize(
    ("flow_source", "step_id", "pass_data"),
    [
        (config_entries.SOURCE_RECONFIGURE, "reconfigure", False),
        (config_entries.SOURCE_REAUTH, "reauth_confirm", True),
    ],
)
async def test_credential_update_invalid_auth(
    hass, mock_sensor_client, flow_source, step_id, pass_data
):
    """Test reauth and reconfigure steps handle invalid credentials correctly."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, entry_id="test", unique_id=MOCK_CONFIG[CONF_USERNAME]
    )
    config_entry.add_to_hass(hass)

    kwargs = {"context": {"source": flow_source, "entry_id": config_entry.entry_id}}
    if pass_data:
        kwargs["data"] = config_entry.data

    result1 = await hass.config_entries.flow.async_init(DOMAIN, **kwargs)
    assert result1["type"] == data_entry_flow.FlowResultType.FORM
    assert result1["step_id"] == step_id

    with patch(
        "custom_components.kingspan_watchman_sensit.config_flow.SENSiTApiClient.async_get_data",
        side_effect=SENSiTAuthError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result1["flow_id"],
            user_input={
                CONF_USERNAME: MOCK_CONFIG[CONF_USERNAME],
                CONF_PASSWORD: "bad-password",
                CONF_NAME: MOCK_CONFIG[CONF_NAME],
            },
        )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["step_id"] == step_id
    assert result2["errors"] == {"base": "auth"}
