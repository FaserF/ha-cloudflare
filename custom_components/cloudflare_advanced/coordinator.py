"""Data update coordinator for Cloudflare Advanced."""

from __future__ import annotations

from datetime import timedelta
import logging
import asyncio
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_TOKEN,
    CONF_EMAIL,
    CONF_API_KEY,
    CONF_ZONES,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from .api import CloudflareApiClient

_LOGGER = logging.getLogger(__name__)


class CloudflareAdvancedCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Cloudflare data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry

        # Get settings from options or data
        self.api_token = entry.options.get(
            CONF_API_TOKEN, entry.data.get(CONF_API_TOKEN)
        )
        self.email = entry.options.get(CONF_EMAIL, entry.data.get(CONF_EMAIL))
        self.api_key = entry.options.get(CONF_API_KEY, entry.data.get(CONF_API_KEY))
        self.zone_ids = entry.data.get(CONF_ZONES, [])
        update_interval = entry.options.get(CONF_UPDATE_INTERVAL, 3600)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

        session = async_get_clientsession(hass)
        self.client = CloudflareApiClient(
            session, api_token=self.api_token, email=self.email, api_key=self.api_key
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all data from Cloudflare and perform automated DDNS updates."""
        data: dict[str, Any] = {
            "zones": {},
            "tunnels": [],
            "public_ip": None,
            "workers": [],
            "turnstile_widgets": [],
            "access_apps": [],
            "pages_projects": [],
        }

        try:
            # 1. Get current public IP (DDNS)
            public_ip = None
            try:
                async with self.client.session.get(
                    "https://services.home-assistant.io/whoami"
                ) as resp:
                    if resp.status == 200:
                        ip_info = await resp.json()
                        public_ip = ip_info.get("ip")
                        data["public_ip"] = public_ip
            except Exception as ip_err:
                _LOGGER.debug("Failed to fetch public IP: %s", ip_err)

            # 2. Fetch all zones
            all_zones = await self.client.get_zones()
            account_id = None

            try:
                accounts = await self.client.get_accounts()
                if accounts:
                    account_id = accounts[0]["id"]
            except Exception as acc_err:
                _LOGGER.debug("Failed to fetch accounts directly: %s", acc_err)

            for zone in all_zones:
                zone_id = zone["id"]
                if zone_id in self.zone_ids:
                    if not account_id:
                        account_id = zone.get("account", {}).get("id")

                    settings_task = self.client.get_zone_settings(zone_id)
                    records_task = self.client.get_dns_records(zone_id)
                    analytics_task = self.client.get_analytics(zone_id)
                    health_checks_task = self.client.get_health_checks(zone_id)
                    page_rules_task = self.client.get_page_rules(zone_id)
                    firewall_task = self.client.get_firewall_events(zone_id)
                    cert_packs_task = self.client.get_certificate_packs(zone_id)
                    email_rules_task = self.client.get_email_routing_rules(zone_id)
                    rulesets_task = self.client.get_zone_rulesets(zone_id)

                    zone_results = await asyncio.gather(
                        settings_task,
                        records_task,
                        analytics_task,
                        health_checks_task,
                        page_rules_task,
                        firewall_task,
                        cert_packs_task,
                        email_rules_task,
                        rulesets_task,
                        return_exceptions=True,
                    )
                    (
                        settings,
                        dns_records,
                        analytics,
                        health_checks,
                        page_rules,
                        firewall,
                        cert_packs,
                        email_rules,
                        rulesets,
                    ) = zone_results

                    waf_rules = []
                    cache_rules = []
                    custom_ruleset_id = None
                    cache_ruleset_id = None
                    if not isinstance(rulesets, Exception) and rulesets:
                        for ruleset in rulesets:
                            if ruleset.get("phase") == "http_request_firewall_custom":
                                custom_ruleset_id = ruleset["id"]
                                try:
                                    waf_rules = await self.client.get_zone_ruleset_rules(
                                        zone_id, custom_ruleset_id
                                    )
                                except Exception as waf_err:
                                    _LOGGER.debug("Failed to fetch WAF rules: %s", waf_err)
                            elif ruleset.get("phase") == "http_request_cache_settings":
                                cache_ruleset_id = ruleset["id"]
                                try:
                                    cache_rules = await self.client.get_zone_ruleset_rules(
                                        zone_id, cache_ruleset_id
                                    )
                                except Exception as cache_err:
                                    _LOGGER.debug("Failed to fetch Cache rules: %s", cache_err)

                    dns_list = (
                        dns_records if not isinstance(dns_records, Exception) else []
                    )

                    # Perform automatic DDNS update if IP changed
                    if public_ip and dns_list:
                        for record in dns_list:
                            if (
                                record.get("type") == "A"
                                and record.get("content") != public_ip
                            ):
                                _LOGGER.info(
                                    "Updating Cloudflare DNS record %s from %s to %s",
                                    record.get("name"),
                                    record.get("content"),
                                    public_ip,
                                )
                                try:
                                    await self.client.update_dns_record(
                                        zone_id,
                                        record["id"],
                                        {
                                            "name": record["name"],
                                            "type": "A",
                                            "content": public_ip,
                                            "proxied": record.get("proxied", True),
                                            "ttl": record.get("ttl", 1),
                                        },
                                    )
                                except Exception as dns_update_err:
                                    _LOGGER.error(
                                        "Failed to update DNS record: %s",
                                        dns_update_err,
                                    )

                    data["zones"][zone_id] = {
                        "info": zone,
                        "settings": settings
                        if not isinstance(settings, Exception)
                        else [],
                        "dns_records": dns_list,
                        "analytics": analytics
                        if not isinstance(analytics, Exception)
                        else {},
                        "health_checks": health_checks
                        if not isinstance(health_checks, Exception)
                        else [],
                        "page_rules": page_rules
                        if not isinstance(page_rules, Exception)
                        else [],
                        "firewall_events": firewall
                        if not isinstance(firewall, Exception)
                        else [],
                        "cert_packs": cert_packs
                        if not isinstance(cert_packs, Exception)
                        else [],
                        "email_rules": email_rules
                        if not isinstance(email_rules, Exception)
                        else [],
                        "waf_rules": waf_rules,
                        "custom_ruleset_id": custom_ruleset_id,
                        "cache_rules": cache_rules,
                        "cache_ruleset_id": cache_ruleset_id,
                    }

            # 3. Fetch Tunnels & Account level services
            if account_id:
                tunnels_task = self.client.get_tunnels(account_id)
                workers_task = self.client.get_workers(account_id)
                turnstile_task = self.client.get_turnstile_widgets(account_id)
                access_task = self.client.get_access_apps(account_id)
                pages_task = self.client.get_pages_projects(account_id)
                gateway_rules_task = self.client.get_gateway_rules(account_id)
                lb_pools_task = self.client.get_load_balancer_pools(account_id)
                registrar_task = self.client.get_registrar_domains(account_id)

                results = await asyncio.gather(
                    tunnels_task,
                    workers_task,
                    turnstile_task,
                    access_task,
                    pages_task,
                    gateway_rules_task,
                    lb_pools_task,
                    registrar_task,
                    return_exceptions=True,
                )
                tunnels, workers, widgets, apps, pages, gateway_rules, lb_pools, registrar = results

                data["workers"] = workers if not isinstance(workers, Exception) else []
                data["turnstile_widgets"] = (
                    widgets if not isinstance(widgets, Exception) else []
                )
                data["access_apps"] = apps if not isinstance(apps, Exception) else []
                data["pages_projects"] = pages if not isinstance(pages, Exception) else []
                data["gateway_rules"] = gateway_rules if not isinstance(gateway_rules, Exception) else []
                data["load_balancer_pools"] = lb_pools if not isinstance(lb_pools, Exception) else []
                data["registrar_domains"] = registrar if not isinstance(registrar, Exception) else []

                tunnels_list = tunnels if not isinstance(tunnels, Exception) else []
                for tunnel in tunnels_list:  # type: ignore[union-attr]
                    tunnel_id = tunnel["id"]
                    connections = await self.client.get_tunnel_connections(
                        account_id, tunnel_id
                    )
                    tunnel["connections"] = connections
                    data["tunnels"].append(tunnel)

            return data

        except Exception as err:
            raise UpdateFailed(
                f"Error communicating with Cloudflare API: {err}"
            ) from err
