"""Binary sensor platform for Cloudflare Advanced."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CloudflareAdvancedCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator: CloudflareAdvancedCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []

    # Add Tunnel Binary Sensors
    for tunnel in coordinator.data.get("tunnels", []):
        entities.append(CloudflareTunnelBinarySensor(coordinator, tunnel))

    # Add Health Check Binary Sensors
    for zone_id, zone_data in coordinator.data.get("zones", {}).items():
        zone_name = zone_data["info"]["name"]
        for check in zone_data.get("health_checks", []):
            entities.append(
                CloudflareHealthCheckBinarySensor(
                    coordinator, zone_id, zone_name, check
                )
            )

    # Add Access Applications Binary Sensors
    for app in coordinator.data.get("access_apps", []):
        entities.append(CloudflareAccessAppBinarySensor(coordinator, app))

    async_add_entities(entities)


class CloudflareTunnelBinarySensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], BinarySensorEntity
):
    """Binary sensor for Cloudflare Tunnels status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        tunnel: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._tunnel_id = tunnel["id"]
        self._tunnel_name = tunnel["name"]
        self._attr_unique_id = f"tunnel_{self._tunnel_id}"
        self._attr_translation_key = "tunnel"
        self._attr_has_entity_name = True

    @property
    def is_on(self) -> bool:
        """Return true if the tunnel is connected/healthy."""
        for t in self.coordinator.data.get("tunnels", []):
            if t["id"] == self._tunnel_id:
                return t.get("status") == "healthy"
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return tunnel details."""
        for t in self.coordinator.data.get("tunnels", []):
            if t["id"] == self._tunnel_id:
                return {
                    "tunnel_id": self._tunnel_id,
                    "connections_count": len(t.get("connections", [])),
                    "status_string": t.get("status"),
                    "connector_version": t.get("connections", [{}])[0].get(
                        "version", "unknown"
                    )
                    if t.get("connections")
                    else "none",
                }
        return {}

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for Zero Trust."""
        config_url = "https://dash.cloudflare.com"
        zones = self.coordinator.data.get("zones", {})
        if zones:
            first_zone = list(zones.values())[0]
            account_id = first_zone.get("info", {}).get("account", {}).get("id")
            if account_id:
                config_url = f"https://dash.cloudflare.com/{account_id}"

        return DeviceInfo(
            identifiers={(DOMAIN, f"tunnel_{self._tunnel_id}")},
            name=f"Cloudflare Tunnel: {self._tunnel_name}",
            manufacturer="Cloudflare Zero Trust",
            configuration_url=config_url,
        )


class CloudflareHealthCheckBinarySensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], BinarySensorEntity
):
    """Binary sensor for Cloudflare Health Checks."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        zone_id: str,
        zone_name: str,
        check: dict[str, Any],
    ) -> None:
        """Initialize the health check sensor."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._check_id = check["id"]
        self._check_name = check.get("name", self._check_id)
        self._attr_unique_id = f"health_check_{self._check_id}"
        self._attr_translation_key = "health_check"
        self._attr_has_entity_name = True
        self._attr_translation_placeholders = {"check_name": self._check_name}

    @property
    def is_on(self) -> bool:
        """Return true if the health check is successful."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        checks = zone_data.get("health_checks", [])

        for c in checks:
            if c["id"] == self._check_id:
                return c.get("status") == "healthy"
        return False

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for the zone."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        account_id = zone_data.get("info", {}).get("account", {}).get("id")
        config_url = "https://dash.cloudflare.com"
        if account_id:
            config_url = f"https://dash.cloudflare.com/{account_id}/{self._zone_name}"

        return DeviceInfo(
            identifiers={(DOMAIN, self._zone_id)},
            name=self._zone_name,
            model=f"Cloudflare Zone Management {self._zone_name}",
            manufacturer="Cloudflare",
            configuration_url=config_url,
        )


class CloudflareAccessAppBinarySensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], BinarySensorEntity
):
    """Binary sensor for Cloudflare Access Applications status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        app: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._app_id = app["id"]
        self._app_name = app.get("name", self._app_id)
        self._attr_unique_id = f"access_app_{self._app_id}"
        self._attr_translation_key = "access_app"
        self._attr_has_entity_name = True
        self._attr_translation_placeholders = {"app_name": self._app_name}

    @property
    def is_on(self) -> bool:
        """Return true if the app is active."""
        for a in self.coordinator.data.get("access_apps", []):
            if a["id"] == self._app_id:
                return a.get("active", True)
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Extra Access stats."""
        for a in self.coordinator.data.get("access_apps", []):
            if a["id"] == self._app_id:
                return {
                    "domain": a.get("domain"),
                    "app_id": self._app_id,
                }
        return {}

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for Account level."""
        config_url = "https://dash.cloudflare.com"
        zones = self.coordinator.data.get("zones", {})
        if zones:
            first_zone = list(zones.values())[0]
            account_id = first_zone.get("info", {}).get("account", {}).get("id")
            if account_id:
                config_url = f"https://dash.cloudflare.com/{account_id}"

        return DeviceInfo(
            identifiers={(DOMAIN, "cloudflare_account_level")},
            name="Cloudflare Account Resources",
            manufacturer="Cloudflare",
            configuration_url=config_url,
        )
