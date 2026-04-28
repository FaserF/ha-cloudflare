"""Switch platform for Cloudflare Advanced."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up the switch platform."""
    coordinator: CloudflareAdvancedCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []

    for zone_id, zone_data in coordinator.data.get("zones", {}).items():
        zone_name = zone_data["info"]["name"]
        entities.append(
            CloudflareSettingSwitch(
                coordinator, zone_id, zone_name, "development_mode", "Development Mode"
            )
        )
        entities.append(
            CloudflareSettingSwitch(
                coordinator, zone_id, zone_name, "always_use_https", "Always Use HTTPS"
            )
        )
        entities.append(
            CloudflareSettingSwitch(
                coordinator,
                zone_id,
                zone_name,
                "automatic_https_rewrites",
                "Automatic HTTPS Rewrites",
            )
        )

        for rule in zone_data.get("page_rules", []):
            entities.append(
                CloudflarePageRuleSwitch(coordinator, zone_id, zone_name, rule)
            )

    async_add_entities(entities)


class CloudflareSettingSwitch(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SwitchEntity
):
    """Switch for a Cloudflare Zone Setting."""

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        zone_id: str,
        zone_name: str,
        setting_id: str,
        setting_label: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._setting_id = setting_id
        self._attr_unique_id = f"{zone_id}_{setting_id}_switch"
        self._attr_translation_key = setting_id
        self._attr_has_entity_name = True

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        settings = zone_data.get("settings", [])

        for setting in settings:
            if setting.get("id") == self._setting_id:
                return setting.get("value") == "on"
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.client.update_zone_setting(
            self._zone_id, self._setting_id, "on"
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.client.update_zone_setting(
            self._zone_id, self._setting_id, "off"
        )
        await self.coordinator.async_request_refresh()

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


class CloudflarePageRuleSwitch(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SwitchEntity
):
    """Switch for a Cloudflare Page Rule."""

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        zone_id: str,
        zone_name: str,
        rule: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._rule_id = rule["id"]
        self._rule = rule
        self._attr_unique_id = f"{zone_id}_pagerule_{self._rule_id}"
        self._attr_translation_key = "page_rule"
        self._attr_has_entity_name = True

        targets = rule.get("targets", [])
        url_target = (
            targets[0].get("constraint", {}).get("value") if targets else "Rule"
        )
        self._attr_translation_placeholders = {"url_target": url_target}

    @property
    def is_on(self) -> bool:
        """Return true if the rule is active."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        rules = zone_data.get("page_rules", [])
        for r in rules:
            if r["id"] == self._rule_id:
                return r.get("status") == "active"
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the rule on."""
        self._rule["status"] = "active"
        await self.coordinator.client.update_page_rule(
            self._zone_id, self._rule_id, self._rule
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the rule off."""
        self._rule["status"] = "disabled"
        await self.coordinator.client.update_page_rule(
            self._zone_id, self._rule_id, self._rule
        )
        await self.coordinator.async_request_refresh()

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
