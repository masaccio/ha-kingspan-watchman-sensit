"""Adds config flow for Kingspan Watchman SENSiT."""

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .api import SENSiTApiClient
from .const import (
    CONF_KINGSPAN_DEBUG,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_USAGE_WINDOW,
    CONF_USERNAME,
    DEFAULT_TANK_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_USAGE_WINDOW,
    DOMAIN,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


class SENSiTFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for kingspan_watchman_sensit."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
    reauth_entry: config_entries.ConfigEntry | None = None

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            valid = await self._test_credentials(username, password)
            if not valid:
                _LOGGER.debug("login failed for username '%s'", username)
                self._errors["base"] = "auth"
            else:
                if self.source == config_entries.SOURCE_REAUTH:
                    _LOGGER.debug("reauthorized username '%s'", username)
                    entry = self._get_reauth_entry()
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={
                            **entry.data,
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                        },
                    )

                # Normal first-time setup
                return self.async_create_entry(title=username, data=user_input)

        return await self._show_config_form(user_input)

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        self.reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        _LOGGER.debug("reauth flow started")
        if user_input is not None:
            return await self.async_step_user()

        return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({}))

    @callback
    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit location data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_TANK_NAME): str,
                }
            ),
            errors=self._errors,
        )

    async def _test_credentials(self, username, password):
        """Return true if credentials is valid."""
        try:
            client = SENSiTApiClient(username, password)
            _ = await client.async_get_data()
            return True
        except Exception:  # pylint: disable=broad-except
            pass
        return False


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Initialise the options flow"""
        if user_input is not None:
            _LOGGER.debug(
                "Config options: %s",
                ", ".join([f"{k}='{v}'" for k, v in user_input.items()]),
            )
            return self.async_create_entry(title=self.config_entry.title, data=user_input)

        options = {
            vol.Optional(
                CONF_UPDATE_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                ),
            ): cv.positive_int,
            vol.Optional(
                CONF_USAGE_WINDOW,
                default=self.config_entry.options.get(CONF_USAGE_WINDOW, DEFAULT_USAGE_WINDOW),
            ): cv.positive_int,
            vol.Optional(
                CONF_KINGSPAN_DEBUG,
                default=self.config_entry.options.get(CONF_KINGSPAN_DEBUG, False),
            ): cv.boolean,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
