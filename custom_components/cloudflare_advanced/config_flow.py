"""Config flow for Cloudflare Advanced integration."""

from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
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
    CONF_ENABLE_DDNS,
    CONF_RECORDS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def get_permissions_summary(probe_results: dict[str, bool]) -> str:
    """Generate a markdown table of token permissions based on active probing."""

    def get_status(key: str) -> str:
        return "✅" if probe_results.get(key, False) else "❌"

    # Define grouped categories for the table
    rows = [
        ("DNS & DDNS", "dns", "No IP updates possible"),
        ("Analytics", "analytics", "No traffic statistics"),
        (
            "Zone Discovery",
            "discovery",
            "Active",
        ),  # Always true if we reached this step
        ("Settings", "settings", "Performance toggles missing"),
        ("Security", "security", "WAF/Firewall rules missing"),
        ("Caching", "caching", "Cache control missing"),
        ("Zero Trust", "zt", "Tunnel info missing"),
        ("Workers / Pages", "workers", "Deployments missing"),
        ("Account Resources", "registrar", "Registrar/Images/LB missing"),
    ]

    header = "| Subsystem | Status | Missing Features |\n| :--- | :---: | :--- |\n"
    table_rows = []

    for name, key, note in rows:
        if key == "discovery":
            status = "✅"
            note_text = "-"
        else:
            status = get_status(key)
            note_text = "-" if status == "✅" else note
        table_rows.append(f"| **{name}** | {status} | {note_text} |")

    return header + "\n".join(table_rows)


class CloudflareAdvancedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Cloudflare Advanced."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return CloudflareAdvancedOptionsFlowHandler()

    def __init__(self) -> None:
        """Initialize the flow."""
        self._api_token: str | None = None
        self._email: str | None = None
        self._api_key: str | None = None
        self._zones: list[dict[str, Any]] = []
        self._selected_zone_ids: list[str] = []
        self._enable_ddns: bool = False
        self._selected_records: list[str] = []
        self._token_info: dict[str, Any] = {}
        self._probe_results: dict[str, bool] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
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
    ) -> config_entries.ConfigFlowResult:
        """Handle API Token step."""
        errors: dict[str, str] = {}
        try:
            if user_input is not None:
                self._api_token = user_input[CONF_API_TOKEN]
                session = async_get_clientsession(self.hass)
                client = CloudflareApiClient(session, api_token=self._api_token)

                if await client.verify_auth():
                    self._token_info = await client.get_token_info()
                    self._zones = await client.get_zones()

                    # Perform active probing
                    accounts = await client.get_accounts()
                    self._probe_results = await client.probe_permissions(
                        self._zones, accounts
                    )

                    if not self._zones:
                        errors["base"] = "no_zones"
                    else:
                        return await self.async_step_verify_token()
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

    async def async_step_verify_token(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step to show token permissions summary."""
        if user_input is not None:
            return await self.async_step_select_zones()

        summary = get_permissions_summary(self._probe_results)

        return self.async_show_form(
            step_id="verify_token",
            description_placeholders={"permissions": summary},
        )

    async def async_step_legacy(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
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
    ) -> config_entries.ConfigFlowResult:
        """Step for selecting zones to monitor."""
        errors: dict[str, str] = {}
        try:
            if user_input is not None:
                self._selected_zone_ids = user_input[CONF_ZONES]
                self._enable_ddns = user_input.get(CONF_ENABLE_DDNS, False)

                unique_id = (
                    self._selected_zone_ids[0]
                    if self._selected_zone_ids
                    else "cloudflare_advanced_entry"
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                if self._enable_ddns:
                    return await self.async_step_select_records()

                return self._async_create_entry()

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
                        vol.Optional(CONF_ENABLE_DDNS, default=False): bool,
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

    async def async_step_select_records(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step for selecting DNS records for DDNS."""
        errors: dict[str, str] = {}
        try:
            if user_input is not None:
                return self._async_create_entry(records=user_input[CONF_RECORDS])

            session = async_get_clientsession(self.hass)
            if self._api_token:
                client = CloudflareApiClient(session, api_token=self._api_token)
            else:
                client = CloudflareApiClient(
                    session, email=self._email, api_key=self._api_key
                )

            all_records = []
            for zone_id in self._selected_zone_ids:
                zone_records = await client.get_dns_records(zone_id)
                all_records.extend(zone_records)

            record_options = {
                rec["id"]: f"{rec['name']} ({rec['type']})"
                for rec in all_records
                if rec["type"] == "A"
            }

            if not record_options:
                return self._async_create_entry()

            return self.async_show_form(
                step_id="select_records",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_RECORDS): selector(
                            {
                                "select": {
                                    "multiple": True,
                                    "options": [
                                        {"value": r_id, "label": r_name}
                                        for r_id, r_name in record_options.items()
                                    ],
                                }
                            }
                        ),
                    }
                ),
                errors=errors,
            )
        except Exception as ex:
            _LOGGER.error(
                "Exception in async_step_select_records: %s", ex, exc_info=True
            )
            errors["base"] = "cannot_connect"
            return self._async_create_entry()

    @callback
    def _async_create_entry(
        self, records: list[str] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create the config entry."""
        data = {
            CONF_ZONES: self._selected_zone_ids,
            CONF_ENABLE_DDNS: self._enable_ddns,
        }
        if self._api_token:
            data[CONF_API_TOKEN] = self._api_token
        else:
            data[CONF_EMAIL] = self._email
            data[CONF_API_KEY] = self._api_key

        if records:
            data[CONF_RECORDS] = records

        account_name = "Cloudflare Advanced"
        if self._zones:
            acc_name = self._zones[0].get("account", {}).get("name")
            if acc_name:
                account_name = f"Cloudflare ({acc_name})"

        return self.async_create_entry(title=account_name, data=data)


class CloudflareAdvancedOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Cloudflare Advanced options."""

    def __init__(self) -> None:
        """Initialize."""
        self._options: dict[str, Any] = {}
        self._token_info: dict[str, Any] = {}
        self._probe_results: dict[str, bool] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            self._options = user_input

            # Check if token changed
            old_token = self.config_entry.options.get(
                CONF_API_TOKEN, self.config_entry.data.get(CONF_API_TOKEN, "")
            )
            new_token = user_input.get(CONF_API_TOKEN)

            if new_token and new_token != old_token:
                session = async_get_clientsession(self.hass)
                client = CloudflareApiClient(session, api_token=new_token)
                self._token_info = await client.get_token_info()

                # Perform active probing
                zones = await client.get_zones()
                accounts = await client.get_accounts()
                self._probe_results = await client.probe_permissions(zones, accounts)

                return await self.async_step_verify_token()

            if user_input.get(CONF_ENABLE_DDNS):
                return await self.async_step_records()
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
        enable_ddns = self.config_entry.options.get(
            CONF_ENABLE_DDNS, self.config_entry.data.get(CONF_ENABLE_DDNS, False)
        )

        options_schema: dict[vol.Required | vol.Optional, Any] = {}

        # Determine if we are using token or legacy auth
        if self.config_entry.data.get(CONF_API_TOKEN):
            options_schema[vol.Required(CONF_API_TOKEN, default=api_token)] = str
        else:
            options_schema[vol.Required(CONF_EMAIL, default=email)] = str
            options_schema[vol.Required(CONF_API_KEY, default=api_key)] = str

        options_schema[vol.Required(CONF_UPDATE_INTERVAL, default=update_interval)] = (
            vol.All(vol.Coerce(int), vol.Range(min=10, max=3600))
        )
        options_schema[vol.Optional(CONF_ENABLE_DDNS, default=enable_ddns)] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options_schema),
        )

    async def async_step_verify_token(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step to show token permissions summary in options."""
        if user_input is not None:
            if self._options.get(CONF_ENABLE_DDNS):
                return await self.async_step_records()
            return self.async_create_entry(title="", data=self._options)

        summary = get_permissions_summary(self._probe_results)

        return self.async_show_form(
            step_id="verify_token",
            description_placeholders={"permissions": summary},
        )

    async def async_step_records(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step for selecting DNS records for DDNS in options."""
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)

        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        client = coordinator.client

        selected_zone_ids = self.config_entry.data.get(CONF_ZONES, [])
        current_records = self.config_entry.options.get(
            CONF_RECORDS, self.config_entry.data.get(CONF_RECORDS, [])
        )

        record_options = {}
        for zone_id in selected_zone_ids:
            try:
                zone_data = coordinator.data.get("zones", {}).get(zone_id, {})
                zone_name = zone_data.get("info", {}).get("name", zone_id)
                records = await client.get_dns_records(zone_id)
                for record in records:
                    if record.get("type") == "A":
                        rec_name = record["name"]
                        rec_id = record["id"]
                        record_options[rec_id] = f"{rec_name} ({zone_name})"
            except Exception as ex:
                _LOGGER.warning("Failed to fetch records for zone %s: %s", zone_id, ex)

        if not record_options:
            return self.async_create_entry(title="", data=self._options)

        return self.async_show_form(
            step_id="records",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RECORDS, default=current_records): selector(
                        {
                            "select": {
                                "multiple": True,
                                "options": [
                                    {"value": r_id, "label": r_name}
                                    for r_id, r_name in record_options.items()
                                ],
                            }
                        }
                    ),
                }
            ),
        )
