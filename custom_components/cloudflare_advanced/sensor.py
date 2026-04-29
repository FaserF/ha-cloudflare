"""Sensor platform for Cloudflare Advanced."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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
    """Set up the sensor platform."""
    coordinator: CloudflareAdvancedCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    # Add Zone Analytics Sensors
    for zone_id, zone_data in coordinator.data.get("zones", {}).items():
        zone_name = zone_data["info"]["name"]
        entities.append(
            CloudflareAnalyticsSensor(coordinator, zone_id, zone_name, "requests")
        )
        entities.append(
            CloudflareAnalyticsSensor(coordinator, zone_id, zone_name, "bytes")
        )
        entities.append(
            CloudflareAnalyticsSensor(coordinator, zone_id, zone_name, "threats")
        )
        entities.append(
            CloudflareAnalyticsSensor(coordinator, zone_id, zone_name, "uniques")
        )
        entities.append(CloudflareFirewallEventSensor(coordinator, zone_id, zone_name))
        entities.append(CloudflareCertificateSensor(coordinator, zone_id, zone_name))

    # Add Worker Sensors
    for worker in coordinator.data.get("workers", []):
        entities.append(CloudflareWorkerSensor(coordinator, worker))

    # Add Turnstile Widgets Sensors
    for widget in coordinator.data.get("turnstile_widgets", []):
        entities.append(CloudflareTurnstileSensor(coordinator, widget))

    # Add Cloudflare Pages Sensors
    for project in coordinator.data.get("pages_projects", []):
        entities.append(CloudflarePagesSensor(coordinator, project))

    # Add Registrar Domain Sensors
    for domain in coordinator.data.get("registrar_domains", []):
        entities.append(CloudflareRegistrarDomainSensor(coordinator, domain))

    # Add Images Sensors
    images_stats = coordinator.data.get("images_stats", {})
    if images_stats:
        entities.append(CloudflareImagesSensor(coordinator, "current"))
        entities.append(CloudflareImagesSensor(coordinator, "allowed"))

    async_add_entities(entities)


class CloudflareAnalyticsSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Analytics."""

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        zone_id: str,
        zone_name: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{zone_id}_analytics_{sensor_type}"

        self._attr_translation_key = sensor_type
        self._attr_has_entity_name = True

        if sensor_type == "bytes":
            self._attr_native_unit_of_measurement = "MB"
        elif sensor_type in ["requests", "threats", "uniques"]:
            self._attr_native_unit_of_measurement = "Count"

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        analytics = zone_data.get("analytics", {})

        if self._sensor_type == "bytes":
            # Convert bytes to Megabytes
            bytes_val = analytics.get("bytes", 0)
            return round(bytes_val / (1024 * 1024), 2)

        return analytics.get(self._sensor_type, 0)

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
            model="Cloudflare Zone Management",
            manufacturer="Cloudflare",
            configuration_url=config_url,
        )


class CloudflareWorkerSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Worker Deployment status."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        worker: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._worker_id = worker["id"]
        self._attr_unique_id = f"worker_{self._worker_id}_deployment"
        self._attr_translation_key = "worker_deployment"
        self._attr_has_entity_name = True
        self._attr_native_unit_of_measurement = "Status"

    @property
    def native_value(self) -> Any:
        """Return status."""
        for w in self.coordinator.data.get("workers", []):
            if w["id"] == self._worker_id:
                return "Active"
        return "Unknown"

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


class CloudflareTurnstileSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Turnstile widgets."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        widget: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._widget_id = widget["sitekey"]
        self._widget_name = widget.get("name", self._widget_id)
        self._attr_unique_id = f"turnstile_{self._widget_id}"
        self._attr_name = f"Turnstile {self._widget_name}"

    @property
    def native_value(self) -> Any:
        """Return the mode."""
        for w in self.coordinator.data.get("turnstile_widgets", []):
            if w["sitekey"] == self._widget_id:
                return w.get("mode", "unknown")
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for Account level."""
        return DeviceInfo(
            identifiers={(DOMAIN, "cloudflare_account_level")},
            name="Cloudflare Account Resources",
            manufacturer="Cloudflare",
            configuration_url="https://dash.cloudflare.com",
        )


class CloudflareFirewallEventSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Firewall/Security events."""

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        zone_id: str,
        zone_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._attr_unique_id = f"{zone_id}_firewall_events"
        self._attr_translation_key = "firewall_events"
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> Any:
        """Return the most recent action blocked."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        events = zone_data.get("firewall_events", [])
        if events:
            return events[0].get("action", "none")
        return "No recent events"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details about the attack."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        events = zone_data.get("firewall_events", [])
        if events:
            ev = events[0]
            return {
                "ip": ev.get("ip"),
                "country": ev.get("country"),
                "rule_id": ev.get("rule_id"),
                "datetime": ev.get("datetime"),
            }
        return {}

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
            model="Cloudflare Zone Management",
            manufacturer="Cloudflare",
            configuration_url=config_url,
        )


class CloudflarePagesSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Pages deployment status."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        project: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._project_name = project["name"]
        self._attr_unique_id = f"pages_{self._project_name}_deployment"
        self._attr_translation_key = "pages_deployment"
        self._attr_has_entity_name = True
        self._attr_translation_placeholders = {"project_name": self._project_name}

    @property
    def native_value(self) -> Any:
        """Return deployment status."""
        for p in self.coordinator.data.get("pages_projects", []):
            if p["name"] == self._project_name:
                latest_deployment = p.get("latest_deployment", {})
                if latest_deployment:
                    return latest_deployment.get("status", "unknown")
                return "No deployments"
        return "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return project details."""
        for p in self.coordinator.data.get("pages_projects", []):
            if p["name"] == self._project_name:
                return {
                    "subdomain": p.get("subdomain"),
                    "production_branch": p.get("production_branch"),
                    "updated_on": p.get("updated_on"),
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


class CloudflareCertificateSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Edge Certificate Expiration."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        zone_id: str,
        zone_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._attr_unique_id = f"{zone_id}_certificate_expiration"
        self._attr_translation_key = "certificate_expiration"
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> Any | None:
        """Return certificate expiration date."""
        from datetime import datetime, timezone
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        cert_packs = zone_data.get("cert_packs", [])
        
        earliest_expiry = None
        for pack in cert_packs:
            for cert in pack.get("certificates", []):
                expires_on = cert.get("expires_on")
                if expires_on:
                    try:
                        dt = datetime.fromisoformat(expires_on.replace("Z", "+00:00"))
                        if earliest_expiry is None or dt < earliest_expiry:
                            earliest_expiry = dt
                    except ValueError:
                        continue
        
        return earliest_expiry

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
            model="Cloudflare Zone Management",
            manufacturer="Cloudflare",
            configuration_url=config_url,
        )


class CloudflareRegistrarDomainSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Registrar Domain expiration."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        domain: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._domain_name = domain["name"]
        self._attr_unique_id = f"registrar_domain_{self._domain_name}"
        self._attr_translation_key = "registrar_domain"
        self._attr_has_entity_name = True
        self._attr_translation_placeholders = {"domain_name": self._domain_name}

    @property
    def native_value(self) -> Any | None:
        """Return the expiration date."""
        from datetime import datetime
        registrar_domains = self.coordinator.data.get("registrar_domains", [])
        for d in registrar_domains:
            if d["name"] == self._domain_name:
                expires_at = d.get("registry_expires_at")
                if expires_at:
                    try:
                        return datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    except ValueError:
                        pass
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return domain attributes."""
        registrar_domains = self.coordinator.data.get("registrar_domains", [])
        for d in registrar_domains:
            if d["name"] == self._domain_name:
                return {
                    "auto_renew": d.get("auto_renew", True),
                    "status": d.get("status", "active"),
                    "privacy": d.get("privacy", True),
                    "registry_created_at": d.get("registry_created_at", ""),
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


class CloudflareImagesSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Images stats."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        stat_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._stat_type = stat_type
        self._attr_unique_id = f"images_stat_{stat_type}"
        self._attr_translation_key = f"images_{stat_type}"
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> Any | None:
        """Return images usage statistics."""
        stats = self.coordinator.data.get("images_stats", {})
        count = stats.get("count", {})
        return count.get(self._stat_type)

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


