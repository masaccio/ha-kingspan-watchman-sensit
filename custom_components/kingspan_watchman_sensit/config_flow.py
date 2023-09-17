"""Adds config flow for Kingspan Watchman SENSiT."""
import logging
from typing import Any, Dict, Optional, Mapping

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries, core
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get,
)

from .api import SENSiTApiClient
from .const import (
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

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            valid = await self._test_credentials(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if valid:
                _LOGGER.debug(
                    "login succeeded for username '%s'", user_input[CONF_USERNAME]
                )
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )
            else:
                _LOGGER.debug(
                    "login failed for username '%s'", user_input[CONF_USERNAME]
                )
                self._errors["base"] = "auth"

            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    async def async_step_reauth(self, user_input: dict | None = None) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")

        return await self.async_step_user()

    @callback
    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

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
        # vol.Required(
        #     CONF_USERNAME, default=self.config_entry.data.get(CONF_USERNAME, "")
        # ): cv.string,
        # vol.Required(
        #     CONF_PASSWORD, default=self.config_entry.data.get(CONF_PASSWORD, "")
        # ): cv.string,
        # vol.Optional(
        #     CONF_NAME,
        #     default=self.config_entry.data.get(CONF_NAME, DEFAULT_TANK_NAME),
        # ): cv.string,

    async def _test_credentials(self, username, password):
        """Return true if credentials is valid."""
        try:
            client = SENSiTApiClient(username, password)
            await client.async_get_data()
            return True
        except Exception:  # pylint: disable=broad-except
            pass
        return False


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self.options = dict(config_entry.options)
        self.options.setdefault(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        self.options.setdefault(CONF_USAGE_WINDOW, DEFAULT_USAGE_WINDOW)

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Initialise the options flow"""
        if user_input is not None:
            _LOGGER.debug(
                "Config options: %s",
                ", ".join([f"{k}='{v}'" for k, v in user_input.items()]),
            )
            return self.async_create_entry(
                title=self.config_entry.title, data=user_input
            )

        options = {
            vol.Optional(
                CONF_UPDATE_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                ),
            ): cv.positive_int,
            vol.Optional(
                CONF_USAGE_WINDOW,
                default=self.config_entry.options.get(
                    CONF_USAGE_WINDOW, DEFAULT_USAGE_WINDOW
                ),
            ): cv.positive_int,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
