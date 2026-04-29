"""Cloudflare API Client."""

from __future__ import annotations

import logging
import aiohttp
from typing import Any
from datetime import datetime, timedelta

from .const import API_URL, GRAPHQL_URL

_LOGGER = logging.getLogger(__name__)


class CloudflareApiClient:
    """Client for Cloudflare API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_token: str | None = None,
        email: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """Initialize the client."""
        self.session = session
        self.api_token = api_token
        self.email = email
        self.api_key = api_key
        self._headers: dict[str, str] = {}

        if api_token:
            self._headers["Authorization"] = f"Bearer {api_token}"
        elif email and api_key:
            self._headers["X-Auth-Email"] = email
            self._headers["X-Auth-Key"] = api_key

        self._headers["Content-Type"] = "application/json"

    async def _request(
        self, method: str, endpoint: str, json_data: dict | None = None
    ) -> dict[str, Any]:
        """Send an HTTP request to the API."""
        url = f"{API_URL}/{endpoint.lstrip('/')}"

        try:
            async with self.session.request(
                method, url, headers=self._headers, json=json_data
            ) as response:
                if response.status == 401:
                    raise Exception("Unauthorized: Check your API token or key.")
                if response.status == 403:
                    raise Exception("Forbidden: Insufficient permissions.")

                try:
                    result = await response.json()
                except Exception:
                    response.raise_for_status()
                    raise Exception(
                        f"HTTP Error {response.status} with non-JSON response"
                    )

                if not result.get("success", False):
                    errors = result.get("errors", [])
                    error_msg = ", ".join(
                        [f"{e.get('message')} ({e.get('code')})" for e in errors]
                    )
                    raise Exception(f"Cloudflare API error: {error_msg}")

                return result
        except aiohttp.ClientError as err:
            _LOGGER.error("Client error communicating with Cloudflare: %s", err)
            raise Exception(f"Connection error: {err}") from err

    async def verify_auth(self) -> bool:
        """Verify authentication credentials."""
        if self.api_token:
            # Token verification endpoint
            try:
                result = await self._request("GET", "user/tokens/verify")
                return result.get("result", {}).get("status") == "active"
            except Exception as err:
                _LOGGER.error("Token verification failed: %s", err)
                return False
        elif self.email and self.api_key:
            # Fallback verification by fetching zones
            try:
                await self.get_zones()
                return True
            except Exception as err:
                _LOGGER.error("Legacy key verification failed: %s", err)
                return False
        return False

    async def get_zones(self) -> list[dict[str, Any]]:
        """Get all zones (domains) in the account."""
        result = await self._request("GET", "zones")
        return result.get("result", [])

    async def get_zone_settings(self, zone_id: str) -> list[dict[str, Any]]:
        """Get settings for a specific zone."""
        result = await self._request("GET", f"zones/{zone_id}/settings")
        return result.get("result", [])

    async def update_zone_setting(self, zone_id: str, setting: str, value: Any) -> Any:
        """Update a specific zone setting."""
        result = await self._request(
            "PATCH", f"zones/{zone_id}/settings/{setting}", json_data={"value": value}
        )
        return result.get("result", {})

    async def get_dns_records(self, zone_id: str) -> list[dict[str, Any]]:
        """Get all DNS records for a specific zone."""
        result = await self._request("GET", f"zones/{zone_id}/dns_records")
        return result.get("result", [])

    async def update_dns_record(
        self, zone_id: str, record_id: str, record_data: dict[str, Any]
    ) -> Any:
        """Update a specific DNS record."""
        result = await self._request(
            "PATCH", f"zones/{zone_id}/dns_records/{record_id}", json_data=record_data
        )
        return result.get("result", {})

    async def purge_cache(
        self,
        zone_id: str,
        purge_everything: bool = True,
        files: list[str] | None = None,
    ) -> Any:
        """Purge cache for a specific zone."""
        data: dict[str, Any] = {}
        if purge_everything:
            data["purge_everything"] = True
        elif files:
            data["files"] = files

        result = await self._request(
            "POST", f"zones/{zone_id}/purge_cache", json_data=data
        )
        return result.get("result", {})

    async def get_tunnels(self, account_id: str) -> list[dict[str, Any]]:
        """Get all Cloudflare Zero Trust Tunnels for an account."""
        try:
            result = await self._request(
                "GET", f"accounts/{account_id}/tunnels?is_deleted=false"
            )
            return result.get("result", [])
        except Exception as err:
            _LOGGER.debug(
                "Failed to fetch tunnels (Account ID required or not authorized): %s",
                err,
            )
            return []

    async def get_tunnel_connections(
        self, account_id: str, tunnel_id: str
    ) -> list[dict[str, Any]]:
        """Get detailed connection status for a tunnel."""
        try:
            result = await self._request(
                "GET", f"accounts/{account_id}/cfd_tunnel/{tunnel_id}/connections"
            )
            return result.get("result", [])
        except Exception as err:
            _LOGGER.debug("Failed to fetch tunnel connections: %s", err)
            return []

    async def get_analytics(self, zone_id: str) -> dict[str, Any]:
        """Get traffic analytics via GraphQL API."""
        now = datetime.now()
        yesterday = now - timedelta(hours=23)
        yesterday_date_str = yesterday.strftime("%Y-%m-%d")

        query = """
        query {
          viewer {
            zones(filter: { zoneTag: "%s" }) {
              httpRequests1dGroups(limit: 1, filter: { date_geq: "%s" }, orderBy: [date_DESC]) {
                dimensions { date }
                sum {
                  requests
                  bytes
                  cachedRequests
                  cachedBytes
                  threats
                }
                uniq {
                  uniques
                }
              }
            }
          }
        }
        """ % (zone_id, yesterday_date_str)

        try:
            async with self.session.post(
                GRAPHQL_URL, headers=self._headers, json={"query": query}
            ) as response:
                if response.status != 200:
                    _LOGGER.warning(
                        "GraphQL analytics request failed with status %s",
                        response.status,
                    )
                    return {}

                result = await response.json()
                if "errors" in result and result["errors"]:
                    _LOGGER.warning(
                        "Cloudflare GraphQL analytics reported errors: %s",
                        result["errors"],
                    )
                    return {}

                data_node = result.get("data")
                if not data_node:
                    return {}

                viewer_node = data_node.get("viewer")
                if not viewer_node:
                    return {}

                zones = viewer_node.get("zones", [])
                if zones and zones[0].get("httpRequests1dGroups"):
                    group = zones[0]["httpRequests1dGroups"][0]
                    combined = {}
                    combined.update(group.get("sum", {}))
                    combined.update(group.get("uniq", {}))
                    return combined
        except Exception as err:
            _LOGGER.warning("GraphQL analytics fetch failed: %s", err)

        return {}

    async def get_health_checks(self, zone_id: str) -> list[dict[str, Any]]:
        """Get health checks for a specific zone."""
        try:
            result = await self._request("GET", f"zones/{zone_id}/health_checks")
            return result.get("result", [])
        except Exception as err:
            _LOGGER.debug("Failed to fetch health checks: %s", err)
            return []

    async def get_workers(self, account_id: str) -> list[dict[str, Any]]:
        """Get all Workers for an account."""
        try:
            result = await self._request(
                "GET", f"accounts/{account_id}/workers/services"
            )
            return result.get("result", [])
        except Exception as err:
            _LOGGER.debug("Failed to fetch Workers: %s", err)
            return []

    async def get_turnstile_widgets(self, account_id: str) -> list[dict[str, Any]]:
        """Get all Turnstile widgets for an account."""
        try:
            result = await self._request(
                "GET", f"accounts/{account_id}/turnstile/widgets"
            )
            return result.get("result", [])
        except Exception as err:
            _LOGGER.debug("Failed to fetch Turnstile widgets: %s", err)
            return []

    async def get_access_apps(self, account_id: str) -> list[dict[str, Any]]:
        """Get all Access applications for an account."""
        try:
            result = await self._request("GET", f"accounts/{account_id}/access/apps")
            return result.get("result", [])
        except Exception as err:
            _LOGGER.debug("Failed to fetch Access apps: %s", err)
            return []

    async def get_pages_projects(self, account_id: str) -> list[dict[str, Any]]:
        """Get all Cloudflare Pages projects for an account."""
        try:
            result = await self._request("GET", f"accounts/{account_id}/pages/projects")
            return result.get("result", [])
        except Exception as err:
            _LOGGER.debug("Failed to fetch Pages projects: %s", err)
            return []


    async def create_dns_record(self, zone_id: str, record_data: dict[str, Any]) -> Any:
        """Create a new DNS record in a zone."""
        result = await self._request(
            "POST", f"zones/{zone_id}/dns_records", json_data=record_data
        )
        return result.get("result", {})

    async def get_page_rules(self, zone_id: str) -> list[dict[str, Any]]:
        """Get all page rules for a zone."""
        try:
            result = await self._request("GET", f"zones/{zone_id}/pagerules")
            return result.get("result", [])
        except Exception as err:
            _LOGGER.debug("Failed to fetch Page Rules: %s", err)
            return []

    async def update_page_rule(
        self, zone_id: str, rule_id: str, rule_data: dict[str, Any]
    ) -> Any:
        """Update a specific page rule."""
        result = await self._request(
            "PUT", f"zones/{zone_id}/pagerules/{rule_id}", json_data=rule_data
        )
        return result.get("result", {})

    async def get_firewall_events(self, zone_id: str) -> list[dict[str, Any]]:
        """Get recent firewall/security events via GraphQL."""
        now = datetime.now()
        yesterday = now - timedelta(hours=23)
        yesterday_datetime_str = yesterday.strftime("%Y-%m-%dT%H:%M:%SZ")

        query = """
        query {
          viewer {
            zones(filter: { zoneTag: "%s" }) {
              firewallEventsAdaptive(limit: 5, filter: { datetime_geq: "%s" }, orderBy: [datetime_DESC]) {
                action
                clientIP
                clientCountryName
                ruleId
                datetime
              }
            }
          }
        }
        """ % (zone_id, yesterday_datetime_str)

        try:
            async with self.session.post(
                GRAPHQL_URL, headers=self._headers, json={"query": query}
            ) as response:
                if response.status != 200:
                    _LOGGER.warning(
                        "GraphQL firewall events request failed with status %s",
                        response.status,
                    )
                    return []

                result = await response.json()
                if "errors" in result and result["errors"]:
                    _LOGGER.warning(
                        "Cloudflare GraphQL firewall events reported errors: %s",
                        result["errors"],
                    )
                    return []

                data_node = result.get("data")
                if not data_node:
                    return []

                viewer_node = data_node.get("viewer")
                if not viewer_node:
                    return []

                zones = viewer_node.get("zones", [])
                if zones and zones[0].get("firewallEventsAdaptive"):
                    events = []
                    for ev in zones[0]["firewallEventsAdaptive"]:
                        events.append(
                            {
                                "action": ev.get("action"),
                                "ip": ev.get("clientIP"),
                                "country": ev.get("clientCountryName"),
                                "rule_id": ev.get("ruleId"),
                                "datetime": ev.get("datetime"),
                            }
                        )
                    return events
        except Exception as err:
            _LOGGER.warning("GraphQL firewall events fetch failed: %s", err)

        return []

    async def get_certificate_packs(self, zone_id: str) -> list[dict[str, Any]]:
        """Get SSL certificate packs for a specific zone."""
        try:
            result = await self._request("GET", f"zones/{zone_id}/ssl/certificate_packs")
            return result.get("result", [])
        except Exception as err:
            _LOGGER.debug("Failed to fetch certificate packs: %s", err)
            return []
