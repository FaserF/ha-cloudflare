"""Diagnostics support for Cloudflare Advanced."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_API_TOKEN, CONF_EMAIL, CONF_API_KEY

TO_REDACT = {
    CONF_API_TOKEN,
    CONF_API_KEY,
    CONF_EMAIL,
    "email",
    "api_token",
    "api_key",
    "ip",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Gather raw coordinator data
    coordinator_data = coordinator.data

    diagnostics_data = {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "data": async_redact_data(coordinator_data, TO_REDACT),
    }

    return diagnostics_data
