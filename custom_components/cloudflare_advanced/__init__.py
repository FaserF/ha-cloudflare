"""The Cloudflare Advanced integration."""

from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .coordinator import CloudflareAdvancedCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cloudflare Advanced from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = CloudflareAdvancedCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as ex:
        raise ConfigEntryNotReady(f"Failed to connect to Cloudflare: {ex}") from ex

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Setup services
    async_setup_services(hass, coordinator)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        async_unload_services(hass)

    return unload_ok
