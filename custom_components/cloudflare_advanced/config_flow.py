"""Config flow for Cloudflare Advanced integration."""

from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import selector

from .api import CloudflareApiClient
from homeassistant.core import callback
from .const import (
    CONF_API_KEY,
    CONF_API_TOKEN,
    CONF_EMAIL,
    CONF_ZONES,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class CloudflareAdvancedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Cloudflare Advanced."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> CloudflareAdvancedOptionsFlowHandler:
        """Get the options flow for this handler."""
        return CloudflareAdvancedOptionsFlowHandler()

    def __init__(self) -> None:
        """Initialize the flow."""
        self._api_token: str | None = None
        self._email: str | None = None
        self._api_key: str | None = None
        self._zones: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            auth_type = user_input.get("auth_type")
            if auth_type == "token":
                return await self.async_step_token()
            return await self.async_step_legacy()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("auth_type", default="token"): vol.In(
                        {
                            "token": "API Token (Empfohlen)",
                            "legacy": "E-Mail + Globaler API Key",
                        }
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_token(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle API Token step."""
        errors: dict[str, str] = {}
        try:
            if user_input is not None:
                self._api_token = user_input[CONF_API_TOKEN]
                session = async_get_clientsession(self.hass)
                client = CloudflareApiClient(session, api_token=self._api_token)

                if await client.verify_auth():
                    self._zones = await client.get_zones()
                    if not self._zones:
                        errors["base"] = "no_zones"
                    else:
                        return await self.async_step_select_zones()
                else:
                    errors["base"] = "invalid_auth"

            return self.async_show_form(
                step_id="token",
                data_schema=vol.Schema({vol.Required(CONF_API_TOKEN): str}),
                errors=errors,
            )
        except Exception as ex:
            _LOGGER.error("Exception in async_step_token: %s", ex, exc_info=True)
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="token",
                data_schema=vol.Schema({vol.Required(CONF_API_TOKEN): str}),
                errors=errors,
            )

    async def async_step_legacy(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Legacy Email + Global Key step."""
        errors: dict[str, str] = {}
        try:
            if user_input is not None:
                self._email = user_input[CONF_EMAIL]
                self._api_key = user_input[CONF_API_KEY]
                session = async_get_clientsession(self.hass)
                client = CloudflareApiClient(
                    session, email=self._email, api_key=self._api_key
                )

                if await client.verify_auth():
                    self._zones = await client.get_zones()
                    if not self._zones:
                        errors["base"] = "no_zones"
                    else:
                        return await self.async_step_select_zones()
                else:
                    errors["base"] = "invalid_auth"

            return self.async_show_form(
                step_id="legacy",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_EMAIL): str,
                        vol.Required(CONF_API_KEY): str,
                    }
                ),
                errors=errors,
            )
        except Exception as ex:
            _LOGGER.error("Exception in async_step_legacy: %s", ex, exc_info=True)
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="legacy",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_EMAIL): str,
                        vol.Required(CONF_API_KEY): str,
                    }
                ),
                errors=errors,
            )

    async def async_step_select_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step for selecting zones to monitor."""
        errors: dict[str, str] = {}
        try:
            if user_input is not None:
                selected_zone_ids = user_input[CONF_ZONES]

                data = {
                    CONF_API_TOKEN: self._api_token,
                    CONF_EMAIL: self._email,
                    CONF_API_KEY: self._api_key,
                    CONF_ZONES: selected_zone_ids,
                }

                unique_id = (
                    selected_zone_ids[0]
                    if selected_zone_ids
                    else "cloudflare_advanced_entry"
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                account_name = "Cloudflare Advanced"
                if self._zones:
                    acc_name = self._zones[0].get("account", {}).get("name")
                    if acc_name:
                        account_name = f"Cloudflare ({acc_name})"

                return self.async_create_entry(title=account_name, data=data)

            zone_options = {zone["id"]: zone["name"] for zone in self._zones}

            return self.async_show_form(
                step_id="select_zones",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_ZONES, default=list(zone_options.keys())
                        ): selector(
                            {
                                "select": {
                                    "multiple": True,
                                    "options": [
                                        {"value": z_id, "label": z_name}
                                        for z_id, z_name in zone_options.items()
                                    ],
                                }
                            }
                        ),
                    }
                ),
                errors=errors,
            )
        except Exception as ex:
            _LOGGER.error("Exception in async_step_select_zones: %s", ex, exc_info=True)
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="token",
                data_schema=vol.Schema({vol.Required(CONF_API_TOKEN): str}),
                errors=errors,
            )


class CloudflareAdvancedOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Cloudflare Advanced options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values
        api_token = self.config_entry.options.get(
            CONF_API_TOKEN, self.config_entry.data.get(CONF_API_TOKEN, "")
        )
        email = self.config_entry.options.get(
            CONF_EMAIL, self.config_entry.data.get(CONF_EMAIL, "")
        )
        api_key = self.config_entry.options.get(
            CONF_API_KEY, self.config_entry.data.get(CONF_API_KEY, "")
        )
        update_interval = self.config_entry.options.get(CONF_UPDATE_INTERVAL, 3600)

        options_schema: dict[vol.Required, Any] = {}

        # Determine if we are using token or legacy auth
        if self.config_entry.data.get(CONF_API_TOKEN):
            options_schema[vol.Required(CONF_API_TOKEN, default=api_token)] = str
        else:
            options_schema[vol.Required(CONF_EMAIL, default=email)] = str
            options_schema[vol.Required(CONF_API_KEY, default=api_key)] = str

        options_schema[vol.Required(CONF_UPDATE_INTERVAL, default=update_interval)] = (
            vol.All(vol.Coerce(int), vol.Range(min=10, max=3600))
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options_schema),
        )
