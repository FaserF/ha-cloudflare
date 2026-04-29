"""Services for Cloudflare Advanced integration."""

from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import CloudflareAdvancedCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_PURGE_CACHE = "purge_cache"
SERVICE_UPDATE_DNS_RECORD = "update_dns_record"
SERVICE_CREATE_DNS_RECORD = "create_dns_record"
SERVICE_UPDATE_RECORDS = "update_records"

PURGE_CACHE_SCHEMA = vol.Schema(
    {
        vol.Required("zone_id"): cv.string,
        vol.Optional("purge_everything", default=True): cv.boolean,
        vol.Optional("files"): vol.All(cv.ensure_list, [cv.string]),
    }
)

UPDATE_DNS_RECORD_SCHEMA = vol.Schema(
    {
        vol.Required("zone_id"): cv.string,
        vol.Required("record_id"): cv.string,
        vol.Required("name"): cv.string,
        vol.Required("type"): cv.string,
        vol.Required("content"): cv.string,
        vol.Optional("proxied", default=True): cv.boolean,
        vol.Optional("ttl", default=1): cv.positive_int,
    }
)

CREATE_DNS_RECORD_SCHEMA = vol.Schema(
    {
        vol.Required("zone_id"): cv.string,
        vol.Required("name"): cv.string,
        vol.Required("type"): cv.string,
        vol.Required("content"): cv.string,
        vol.Optional("proxied", default=True): cv.boolean,
        vol.Optional("ttl", default=1): cv.positive_int,
    }
)


def async_setup_services(
    hass: HomeAssistant, coordinator: CloudflareAdvancedCoordinator
) -> None:
    """Set up services."""

    async def async_handle_purge_cache(call: ServiceCall) -> None:
        """Handle purge cache service."""
        zone_id = call.data["zone_id"]
        purge_everything = call.data["purge_everything"]
        files = call.data.get("files")

        try:
            await coordinator.client.purge_cache(zone_id, purge_everything, files)
            _LOGGER.info("Successfully purged Cloudflare cache for zone %s", zone_id)
        except Exception as ex:
            _LOGGER.error(
                "Failed to purge Cloudflare cache for zone %s: %s", zone_id, ex
            )

    async def async_handle_update_dns_record(call: ServiceCall) -> None:
        """Handle update DNS record service."""
        zone_id = call.data["zone_id"]
        record_id = call.data["record_id"]

        record_data = {
            "name": call.data["name"],
            "type": call.data["type"],
            "content": call.data["content"],
            "proxied": call.data["proxied"],
            "ttl": call.data["ttl"],
        }

        try:
            await coordinator.client.update_dns_record(zone_id, record_id, record_data)
            _LOGGER.info(
                "Successfully updated Cloudflare DNS record %s in zone %s",
                record_id,
                zone_id,
            )
            await coordinator.async_request_refresh()
        except Exception as ex:
            _LOGGER.error(
                "Failed to update Cloudflare DNS record %s in zone %s: %s",
                record_id,
                zone_id,
                ex,
            )

    async def async_handle_create_dns_record(call: ServiceCall) -> None:
        """Handle create DNS record service."""
        zone_id = call.data["zone_id"]

        record_data = {
            "name": call.data["name"],
            "type": call.data["type"],
            "content": call.data["content"],
            "proxied": call.data["proxied"],
            "ttl": call.data["ttl"],
        }

        try:
            await coordinator.client.create_dns_record(zone_id, record_data)
            _LOGGER.info(
                "Successfully created Cloudflare DNS record %s in zone %s",
                call.data["name"],
                zone_id,
            )
            await coordinator.async_request_refresh()
        except Exception as ex:
            _LOGGER.error(
                "Failed to create Cloudflare DNS record %s in zone %s: %s",
                call.data["name"],
                zone_id,
                ex,
            )

    async def async_handle_update_records(call: ServiceCall) -> None:
        """Handle update records service (trigger DDNS)."""
        _LOGGER.info("Triggering Cloudflare DDNS update")
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_PURGE_CACHE, async_handle_purge_cache, schema=PURGE_CACHE_SCHEMA
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_DNS_RECORD,
        async_handle_update_dns_record,
        schema=UPDATE_DNS_RECORD_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_RECORDS,
        async_handle_update_records,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_DNS_RECORD,
        async_handle_create_dns_record,
        schema=CREATE_DNS_RECORD_SCHEMA,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, SERVICE_PURGE_CACHE)
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_DNS_RECORD)
    hass.services.async_remove(DOMAIN, SERVICE_CREATE_DNS_RECORD)
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_RECORDS)
