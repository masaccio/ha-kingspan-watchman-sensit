"""Config flow for Kingspan Watchman SENSiT."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import homeassistant.helpers.config_validation as cv
import probatio as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .api import (
    SENSiTApiClient,
    SENSiTAuthError,
    SENSiTConnectionError,
    SENSiTNoDataError,
)
from .const import (
    CONF_KINGSPAN_DEBUG,
    CONF_NAME,
    CONF_OIL_ENERGY_DENSITY,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_USAGE_WINDOW,
    CONF_USERNAME,
    DEFAULT_OIL_ENERGY_DENSITY,
    DEFAULT_TANK_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_USAGE_WINDOW,
    DOMAIN,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


class SENSiTFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for kingspan_watchman_sensit."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._errors: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(username.casefold())
            self._abort_if_unique_id_configured()

            error = await self._test_credentials(username, password)
            if error is None:
                return self.async_create_entry(title=username, data=user_input)

            self._errors["base"] = error

        return await self._show_config_form(
            step_id="user",
            defaults=user_input,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        self._errors = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(username.casefold())
            self._abort_if_unique_id_mismatch()

            error = await self._test_credentials(username, password)
            if error is None:
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    title=username,
                    data_updates={
                        **reconfigure_entry.data,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_NAME: user_input.get(
                            CONF_NAME,
                            reconfigure_entry.data.get(CONF_NAME, DEFAULT_TANK_NAME),
                        ),
                    },
                )

            self._errors["base"] = error

        defaults = {
            CONF_USERNAME: reconfigure_entry.data.get(CONF_USERNAME, ""),
            CONF_PASSWORD: reconfigure_entry.data.get(CONF_PASSWORD, ""),
            CONF_NAME: reconfigure_entry.data.get(CONF_NAME, DEFAULT_TANK_NAME),
        }
        return await self._show_config_form(
            step_id="reconfigure",
            defaults=user_input or defaults,
        )

    async def async_step_reauth(
        self, _entry_data: Mapping[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm and handle the re-authentication flow."""
        self._errors = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            error = await self._test_credentials(username, password)
            if error is None:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        **reauth_entry.data,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )
            self._errors["base"] = error

        defaults = {
            CONF_USERNAME: reauth_entry.data.get(CONF_USERNAME, ""),
            CONF_PASSWORD: "",
            CONF_NAME: reauth_entry.data.get(CONF_NAME, DEFAULT_TANK_NAME),
        }
        return await self._show_config_form(
            step_id="reauth_confirm",
            defaults=user_input or defaults,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    async def _show_config_form(
        self,
        step_id: str = "user",
        defaults: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the configuration form."""
        defaults = defaults or {}
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): str,
                    vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): str,
                    vol.Optional(
                        CONF_NAME,
                        default=defaults.get(CONF_NAME, DEFAULT_TANK_NAME),
                    ): str,
                }
            ),
            errors=self._errors,
        )

    async def _test_credentials(self, username: str, password: str) -> str | None:
        """Return None if credentials are valid, or an error key string."""
        try:
            client = SENSiTApiClient(username, password)
            await client.async_get_data()
        except SENSiTAuthError:
            return "auth"
        except SENSiTConnectionError:
            return "cannot_connect"
        except SENSiTNoDataError:
            return "no_data"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception testing credentials")
            return "unknown_error"
        return None

    def is_matching(self, other_flow: object) -> bool:
        """Return whether this flow matches another flow."""
        return False


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Initialize the options flow."""
        if user_input is not None:
            _LOGGER.debug(
                "Config options: %s",
                ", ".join([f"{k}='{v}'" for k, v in user_input.items()]),
            )
            return self.async_create_entry(title="", data=user_input)

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
                CONF_OIL_ENERGY_DENSITY,
                default=self.config_entry.options.get(
                    CONF_OIL_ENERGY_DENSITY, DEFAULT_OIL_ENERGY_DENSITY
                ),
            ): cv.positive_float,
            vol.Optional(
                CONF_KINGSPAN_DEBUG,
                default=self.config_entry.options.get(CONF_KINGSPAN_DEBUG, False),
            ): cv.boolean,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
