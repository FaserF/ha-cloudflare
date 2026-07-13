"""Sensor platform for Cloudflare Advanced."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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
        entities.append(CloudflareCacheRatioSensor(coordinator, zone_id, zone_name))
        entities.append(
            CloudflareTopThreatCountriesSensor(coordinator, zone_id, zone_name)
        )

    # Add Worker Sensors
    for worker in coordinator.data.get("workers", []):
        entities.append(CloudflareWorkerSensor(coordinator, worker))

    # Add Turnstile Widgets Sensors
    for widget in coordinator.data.get("turnstile_widgets", []):
        entities.append(CloudflareTurnstileSensor(coordinator, widget))

    # Add Cloudflare Pages Sensors (one device per project, multiple sensors)
    for project in coordinator.data.get("pages_projects", []):
        project_name = project["name"]
        entities.extend(
            [
                CloudflarePagesStatusSensor(coordinator, project_name),
                CloudflarePagesLastDeployedSensor(coordinator, project_name),
                CloudflarePagesBranchSensor(coordinator, project_name),
                CloudflarePagesUrlSensor(coordinator, project_name),
                CloudflarePagesDeploymentStageSensor(coordinator, project_name),
                CloudflarePagesEnvironmentSensor(coordinator, project_name),
                CloudflarePagesTriggerTypeSensor(coordinator, project_name),
                CloudflarePagesCommitHashSensor(coordinator, project_name),
            ]
        )

    # Add Registrar Domain Sensors
    for domain in coordinator.data.get("registrar_domains", []):
        entities.append(CloudflareRegistrarDomainSensor(coordinator, domain))

    # Add Images Sensors
    images_stats = coordinator.data.get("images_stats", {})
    if images_stats:
        entities.append(CloudflareImagesSensor(coordinator, "current"))
        entities.append(CloudflareImagesSensor(coordinator, "allowed"))

    # Add Account Level / API Limit Sensors
    entities.append(CloudflareRatelimitSensor(coordinator, "remaining"))
    entities.append(CloudflareRatelimitSensor(coordinator, "reset"))

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

        # Disable rarely used analytics by default
        if sensor_type in ["threats", "uniques"]:
            self._attr_entity_registry_enabled_default = False

        icons = {
            "requests": "mdi:chart-bar",
            "bytes": "mdi:download-network",
            "threats": "mdi:shield-alert",
            "uniques": "mdi:account-multiple",
        }
        self._attr_icon = icons.get(sensor_type)

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
    _attr_icon = "mdi:cog-transfer"

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
    _attr_icon = "mdi:shield-check"

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

    _attr_icon = "mdi:shield-lock"

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


class CloudflarePagesBaseSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Base sensor for a Cloudflare Pages project sensor."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        project_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._project_name = project_name

    def _get_project(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        for project in self.coordinator.data.get("pages_projects", []):
            if project["name"] == self._project_name:
                return project
        return None

    def _get_latest_deployment(self) -> dict[str, Any] | None:
        project = self._get_project()
        if project:
            return project.get("latest_deployment") or None
        return None

    def _get_account_id(self) -> str | None:
        zones = self.coordinator.data.get("zones", {})
        if zones:
            first_zone = list(zones.values())[0]
            return first_zone.get("info", {}).get("account", {}).get("id")
        return None

    @property
    def available(self) -> bool:
        """Return False when project no longer exists in coordinator data."""
        return super().available and self._get_project() is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for this Pages project."""
        account_id = self._get_account_id()
        config_url = (
            f"https://dash.cloudflare.com/{account_id}/pages/view/{self._project_name}"
            if account_id
            else "https://dash.cloudflare.com"
        )
        return DeviceInfo(
            identifiers={(DOMAIN, f"pages_{self._project_name}")},
            name=self._project_name,
            model="Cloudflare Pages",
            manufacturer="Cloudflare",
            configuration_url=config_url,
        )


class CloudflarePagesStatusSensor(CloudflarePagesBaseSensor):
    """Sensor for Pages deployment status."""

    _attr_entity_registry_enabled_default = True
    _attr_icon = "mdi:cloud-check"

    def __init__(
        self, coordinator: CloudflareAdvancedCoordinator, project_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, project_name)
        self._attr_unique_id = f"pages_{project_name}_status"
        self._attr_translation_key = "pages_status"

    @property
    def native_value(self) -> str | None:
        """Return deployment status from latest stage."""
        deployment = self._get_latest_deployment()
        if deployment is None:
            return None
        latest_stage = deployment.get("latest_stage", {})
        return latest_stage.get("status") if latest_stage else None


class CloudflarePagesLastDeployedSensor(CloudflarePagesBaseSensor):
    """Sensor for Pages last deployment timestamp."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_registry_enabled_default = True
    _attr_icon = "mdi:clock-check"

    def __init__(
        self, coordinator: CloudflareAdvancedCoordinator, project_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, project_name)
        self._attr_unique_id = f"pages_{project_name}_last_deployed"
        self._attr_translation_key = "pages_last_deployed"

    @property
    def native_value(self) -> Any | None:
        """Return when the latest deployment was created."""
        deployment = self._get_latest_deployment()
        if deployment is None:
            return None
        created_at = deployment.get("created_on")
        if created_at:
            try:
                return datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                pass
        return None


class CloudflarePagesBranchSensor(CloudflarePagesBaseSensor):
    """Sensor for Pages deployment branch."""

    _attr_entity_registry_enabled_default = True
    _attr_icon = "mdi:source-branch"

    def __init__(
        self, coordinator: CloudflareAdvancedCoordinator, project_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, project_name)
        self._attr_unique_id = f"pages_{project_name}_branch"
        self._attr_translation_key = "pages_branch"

    @property
    def native_value(self) -> str | None:
        """Return branch that triggered latest deployment."""
        deployment = self._get_latest_deployment()
        if deployment is None:
            return None
        return (
            deployment.get("deployment_trigger", {}).get("metadata", {}).get("branch")
        )


class CloudflarePagesUrlSensor(CloudflarePagesBaseSensor):
    """Sensor for Pages deployment URL."""

    _attr_entity_registry_enabled_default = True
    _attr_icon = "mdi:link"

    def __init__(
        self, coordinator: CloudflareAdvancedCoordinator, project_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, project_name)
        self._attr_unique_id = f"pages_{project_name}_url"
        self._attr_translation_key = "pages_url"

    @property
    def native_value(self) -> str | None:
        """Return deployment subdomain (first segment of pages.dev URL)."""
        deployment = self._get_latest_deployment()
        if deployment is None:
            return None
        url = deployment.get("url", "")
        host = url.removeprefix("https://").removeprefix("http://")
        return host.split(".")[0] if host else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return full deployment URL."""
        deployment = self._get_latest_deployment()
        if deployment is None:
            return {}
        url = deployment.get("url")
        return {"url": url} if url else {}


class CloudflarePagesDeploymentStageSensor(CloudflarePagesBaseSensor):
    """Sensor for Pages current deployment stage."""

    _attr_entity_registry_enabled_default = True
    _attr_icon = "mdi:layers-outline"

    def __init__(
        self, coordinator: CloudflareAdvancedCoordinator, project_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, project_name)
        self._attr_unique_id = f"pages_{project_name}_stage"
        self._attr_translation_key = "pages_stage"

    @property
    def native_value(self) -> str | None:
        """Return current stage name of latest deployment."""
        deployment = self._get_latest_deployment()
        if deployment is None:
            return None
        latest_stage = deployment.get("latest_stage", {})
        return latest_stage.get("name") if latest_stage else None


class CloudflarePagesEnvironmentSensor(CloudflarePagesBaseSensor):
    """Sensor for Pages deployment environment."""

    _attr_entity_registry_enabled_default = True
    _attr_icon = "mdi:server"

    def __init__(
        self, coordinator: CloudflareAdvancedCoordinator, project_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, project_name)
        self._attr_unique_id = f"pages_{project_name}_environment"
        self._attr_translation_key = "pages_environment"

    @property
    def native_value(self) -> str | None:
        """Return environment of latest deployment (production/preview)."""
        deployment = self._get_latest_deployment()
        if deployment is None:
            return None
        return deployment.get("environment")


class CloudflarePagesTriggerTypeSensor(CloudflarePagesBaseSensor):
    """Sensor for Pages deployment trigger type."""

    _attr_entity_registry_enabled_default = True
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self, coordinator: CloudflareAdvancedCoordinator, project_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, project_name)
        self._attr_unique_id = f"pages_{project_name}_trigger_type"
        self._attr_translation_key = "pages_trigger_type"

    @property
    def native_value(self) -> str | None:
        """Return trigger type of latest deployment."""
        deployment = self._get_latest_deployment()
        if deployment is None:
            return None
        return deployment.get("deployment_trigger", {}).get("type")


class CloudflarePagesCommitHashSensor(CloudflarePagesBaseSensor):
    """Sensor for Pages deployment commit hash."""

    _attr_entity_registry_enabled_default = True
    _attr_icon = "mdi:source-commit"

    def __init__(
        self, coordinator: CloudflareAdvancedCoordinator, project_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, project_name)
        self._attr_unique_id = f"pages_{project_name}_commit_hash"
        self._attr_translation_key = "pages_commit_hash"

    @property
    def native_value(self) -> str | None:
        """Return short (7-char) commit hash of latest deployment."""
        deployment = self._get_latest_deployment()
        if deployment is None:
            return None
        full_hash = (
            deployment.get("deployment_trigger", {})
            .get("metadata", {})
            .get("commit_hash")
        )
        return full_hash[:7] if full_hash else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return full commit metadata."""
        deployment = self._get_latest_deployment()
        if deployment is None:
            return {}
        metadata = deployment.get("deployment_trigger", {}).get("metadata", {})
        attrs: dict[str, Any] = {
            "full_hash": metadata.get("commit_hash"),
            "commit_message": metadata.get("commit_message"),
            "branch": metadata.get("branch"),
            "repo_name": metadata.get("repo_name"),
            "repo_owner": metadata.get("repo_owner"),
            "deployment_id": deployment.get("id"),
        }
        if pr_id := metadata.get("pr_id"):
            attrs["pr_id"] = pr_id
        return {k: v for k, v in attrs.items() if v is not None}


class CloudflareCertificateSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Edge Certificate Expiration."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:certificate"

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
        """Return earliest certificate expiration date across all packs."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        cert_packs = zone_data.get("cert_packs", [])

        earliest_expiry = None
        for pack in cert_packs:
            candidates = [
                cert.get("expires_on") for cert in pack.get("certificates", [])
            ]
            if not candidates:
                candidates = [pack.get("expires_on")]
            for expires_on in candidates:
                if not expires_on:
                    continue
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
    _attr_icon = "mdi:domain"

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
    _attr_icon = "mdi:image-multiple"

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


class CloudflareRatelimitSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare API Rate Limit."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_unique_id = f"cloudflare_ratelimit_{sensor_type}"
        self._attr_translation_key = f"ratelimit_{sensor_type}"
        self._attr_has_entity_name = True

        if sensor_type == "remaining":
            self._attr_native_unit_of_measurement = "Requests"
            self._attr_icon = "mdi:api"
        elif sensor_type == "reset":
            self._attr_native_unit_of_measurement = "s"
            self._attr_icon = "mdi:timer-sand"

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.coordinator.data.get("ratelimit", {}).get(self._sensor_type)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "cloudflare_account_level")},
            name="Cloudflare Account Resources",
            manufacturer="Cloudflare",
            configuration_url="https://dash.cloudflare.com",
        )


class CloudflareCacheRatioSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Cache Ratio (percentage of bytes served from cache)."""

    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:database-arrow-down"
    _attr_native_unit_of_measurement = "%"
    _attr_has_entity_name = True

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
        self._attr_unique_id = f"{zone_id}_cache_ratio"
        self._attr_translation_key = "cache_ratio"

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        analytics = zone_data.get("analytics", {})
        total_bytes = analytics.get("bytes", 0)
        cached_bytes = analytics.get("cachedBytes", 0)
        if total_bytes > 0:
            return round((cached_bytes / total_bytes) * 100, 2)
        return 0.0

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


class CloudflareTopThreatCountriesSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Top Threat Countries."""

    _attr_icon = "mdi:earth"
    _attr_has_entity_name = True

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
        self._attr_unique_id = f"{zone_id}_top_threat_countries"
        self._attr_translation_key = "top_threat_countries"

    @property
    def native_value(self) -> str:
        """Return the top threat country."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        events = zone_data.get("firewall_events", [])
        if not events:
            return "No threats"

        country_counts: dict[str, int] = {}
        for ev in events:
            country = ev.get("country")
            if country:
                country_counts[country] = country_counts.get(country, 0) + 1

        if not country_counts:
            return "No threats"

        top_country = max(country_counts, key=country_counts.get)
        return top_country

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return threat countries counts."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        events = zone_data.get("firewall_events", [])
        country_counts: dict[str, int] = {}
        for ev in events:
            country = ev.get("country")
            if country:
                country_counts[country] = country_counts.get(country, 0) + 1

        return {
            "country_counts": country_counts,
            "total_recent_threats": len(events),
        }

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
