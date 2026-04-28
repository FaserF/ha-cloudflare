"""Sensor platform for Cloudflare Advanced."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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

    # Add Worker Sensors
    for worker in coordinator.data.get("workers", []):
        entities.append(CloudflareWorkerSensor(coordinator, worker))

    # Add Turnstile Widgets Sensors
    for widget in coordinator.data.get("turnstile_widgets", []):
        entities.append(CloudflareTurnstileSensor(coordinator, widget))

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
    def device_info(self) -> dict[str, Any]:
        """Device info for the zone."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        account_id = zone_data.get("info", {}).get("account", {}).get("id")
        config_url = "https://dash.cloudflare.com"
        if account_id:
            config_url = f"https://dash.cloudflare.com/{account_id}/{self._zone_name}"

        return {
            "identifiers": {(DOMAIN, self._zone_id)},
            "name": self._zone_name,
            "model": f"Cloudflare Zone Management {self._zone_name}",
            "manufacturer": "Cloudflare",
            "configuration_url": config_url,
        }


class CloudflareWorkerSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Worker Deployment status."""

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
    def device_info(self) -> dict[str, Any]:
        """Device info for Account level."""
        config_url = "https://dash.cloudflare.com"
        zones = self.coordinator.data.get("zones", {})
        if zones:
            first_zone = list(zones.values())[0]
            account_id = first_zone.get("info", {}).get("account", {}).get("id")
            if account_id:
                config_url = f"https://dash.cloudflare.com/{account_id}"

        return {
            "identifiers": {(DOMAIN, "cloudflare_account_level")},
            "name": "Cloudflare Account Resources",
            "manufacturer": "Cloudflare",
            "configuration_url": config_url,
        }


class CloudflareTurnstileSensor(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SensorEntity
):
    """Sensor for Cloudflare Turnstile widgets."""

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
    def device_info(self) -> dict[str, Any]:
        """Device info for Account level."""
        return {
            "identifiers": {(DOMAIN, "cloudflare_account_level")},
            "name": "Cloudflare Account Resources",
            "manufacturer": "Cloudflare",
            "configuration_url": "https://dash.cloudflare.com",
        }


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
    def device_info(self) -> dict[str, Any]:
        """Device info for the zone."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        account_id = zone_data.get("info", {}).get("account", {}).get("id")
        config_url = "https://dash.cloudflare.com"
        if account_id:
            config_url = f"https://dash.cloudflare.com/{account_id}/{self._zone_name}"

        return {
            "identifiers": {(DOMAIN, self._zone_id)},
            "name": self._zone_name,
            "model": f"Cloudflare Zone Management {self._zone_name}",
            "manufacturer": "Cloudflare",
            "configuration_url": config_url,
        }
