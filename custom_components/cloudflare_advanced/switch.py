"""Switch platform for Cloudflare Advanced."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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

        for email_rule in zone_data.get("email_rules", []):
            entities.append(
                CloudflareEmailRoutingSwitch(coordinator, zone_id, zone_name, email_rule)
            )

        for waf_rule in zone_data.get("waf_rules", []):
            entities.append(
                CloudflareWafRuleSwitch(coordinator, zone_id, zone_name, waf_rule)
            )

        for cache_rule in zone_data.get("cache_rules", []):
            entities.append(
                CloudflareCacheRuleSwitch(coordinator, zone_id, zone_name, cache_rule)
            )

    for gateway_rule in coordinator.data.get("gateway_rules", []):
        entities.append(CloudflareGatewayRuleSwitch(coordinator, gateway_rule))

    for domain in coordinator.data.get("registrar_domains", []):
        entities.append(CloudflareRegistrarAutoRenewSwitch(coordinator, domain))

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


class CloudflarePageRuleSwitch(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SwitchEntity
):
    """Switch for a Cloudflare Page Rule."""

    _attr_entity_registry_enabled_default = False

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


class CloudflareEmailRoutingSwitch(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SwitchEntity
):
    """Switch for a Cloudflare Email Routing Rule."""

    _attr_entity_registry_enabled_default = False

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
        self._attr_unique_id = f"{zone_id}_email_routing_{self._rule_id}"
        self._attr_translation_key = "email_routing"
        self._attr_has_entity_name = True

        matchers = rule.get("matchers", [])
        alias = (
            matchers[0].get("value") if matchers else "Email Rule"
        )
        self._attr_translation_placeholders = {"alias": alias}

    @property
    def is_on(self) -> bool:
        """Return true if the rule is active."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        rules = zone_data.get("email_rules", [])
        for r in rules:
            if r["id"] == self._rule_id:
                return r.get("enabled", False)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the rule on."""
        self._rule["enabled"] = True
        payload = {
            "actions": self._rule.get("actions", []),
            "matchers": self._rule.get("matchers", []),
            "enabled": True,
            "name": self._rule.get("name", "")
        }
        await self.coordinator.client.update_email_routing_rule(
            self._zone_id, self._rule_id, payload
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the rule off."""
        self._rule["enabled"] = False
        payload = {
            "actions": self._rule.get("actions", []),
            "matchers": self._rule.get("matchers", []),
            "enabled": False,
            "name": self._rule.get("name", "")
        }
        await self.coordinator.client.update_email_routing_rule(
            self._zone_id, self._rule_id, payload
        )
        await self.coordinator.async_request_refresh()

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


class CloudflareGatewayRuleSwitch(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SwitchEntity
):
    """Switch for a Cloudflare Zero Trust Gateway Rule."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        rule: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._rule_id = rule["id"]
        self._rule = rule
        self._attr_unique_id = f"gateway_rule_{self._rule_id}"
        self._attr_translation_key = "gateway_rule"
        self._attr_has_entity_name = True
        
        rule_name = rule.get("name", "Gateway Rule")
        self._attr_translation_placeholders = {"rule_name": rule_name}

    @property
    def is_on(self) -> bool:
        """Return true if the rule is active."""
        rules = self.coordinator.data.get("gateway_rules", [])
        for r in rules:
            if r["id"] == self._rule_id:
                return r.get("enabled", False)
        return False

    async def _update_rule(self, enabled: bool) -> None:
        """Update the rule enabled status."""
        zones = self.coordinator.data.get("zones", {})
        account_id = None
        if zones:
            account_id = list(zones.values())[0].get("info", {}).get("account", {}).get("id")
        
        if not account_id:
            try:
                accounts = await self.coordinator.client.get_accounts()
                if accounts:
                    account_id = accounts[0]["id"]
            except Exception:
                pass

        if not account_id:
            return

        payload = {
            "name": self._rule.get("name", ""),
            "enabled": enabled,
            "action": self._rule.get("action", ""),
            "filters": self._rule.get("filters", []),
            "conditions": self._rule.get("conditions", []),
            "description": self._rule.get("description", ""),
            "rule_settings": self._rule.get("rule_settings", {}),
        }
        await self.coordinator.client.update_gateway_rule(
            account_id, self._rule_id, payload
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the rule on."""
        await self._update_rule(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the rule off."""
        await self._update_rule(False)

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


class CloudflareWafRuleSwitch(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SwitchEntity
):
    """Switch for a Cloudflare WAF Custom Rule."""

    _attr_entity_registry_enabled_default = False

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
        self._attr_unique_id = f"{zone_id}_waf_rule_{self._rule_id}"
        self._attr_translation_key = "waf_rule"
        self._attr_has_entity_name = True

        rule_desc = rule.get("description", "WAF Rule")
        self._attr_translation_placeholders = {"rule_desc": rule_desc}

    @property
    def is_on(self) -> bool:
        """Return true if the rule is active."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        rules = zone_data.get("waf_rules", [])
        for r in rules:
            if r["id"] == self._rule_id:
                return r.get("enabled", False)
        return False

    async def _update_rule(self, enabled: bool) -> None:
        """Update the rule enabled status."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        ruleset_id = zone_data.get("custom_ruleset_id")
        if not ruleset_id:
            return

        await self.coordinator.client.update_zone_ruleset_rule(
            self._zone_id, ruleset_id, self._rule_id, enabled
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the rule on."""
        await self._update_rule(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the rule off."""
        await self._update_rule(False)

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


class CloudflareCacheRuleSwitch(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SwitchEntity
):
    """Switch for a Cloudflare Cache Rule."""

    _attr_entity_registry_enabled_default = False

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
        self._attr_unique_id = f"{zone_id}_cache_rule_{self._rule_id}"
        self._attr_translation_key = "cache_rule"
        self._attr_has_entity_name = True

        rule_desc = rule.get("description", "Cache Rule")
        self._attr_translation_placeholders = {"rule_desc": rule_desc}

    @property
    def is_on(self) -> bool:
        """Return true if the rule is active."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        rules = zone_data.get("cache_rules", [])
        for r in rules:
            if r["id"] == self._rule_id:
                return r.get("enabled", False)
        return False

    async def _update_rule(self, enabled: bool) -> None:
        """Update the rule enabled status."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        ruleset_id = zone_data.get("cache_ruleset_id")
        if not ruleset_id:
            return

        await self.coordinator.client.update_zone_ruleset_rule(
            self._zone_id, ruleset_id, self._rule_id, enabled
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the rule on."""
        await self._update_rule(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the rule off."""
        await self._update_rule(False)

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


class CloudflareRegistrarAutoRenewSwitch(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SwitchEntity
):
    """Switch for a Cloudflare Registrar Domain Auto-Renew status."""

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        domain: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._domain_name = domain["name"]
        self._attr_unique_id = f"registrar_domain_auto_renew_{self._domain_name}"
        self._attr_translation_key = "registrar_auto_renew"
        self._attr_has_entity_name = True
        self._attr_translation_placeholders = {"domain_name": self._domain_name}

    @property
    def is_on(self) -> bool:
        """Return true if the domain auto-renews."""
        registrar_domains = self.coordinator.data.get("registrar_domains", [])
        for d in registrar_domains:
            if d["name"] == self._domain_name:
                return d.get("auto_renew", True)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on auto-renew."""
        await self._update_auto_renew(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off auto-renew."""
        await self._update_auto_renew(False)

    async def _update_auto_renew(self, enabled: bool) -> None:
        """Update the auto-renew status via API."""
        zones = self.coordinator.data.get("zones", {})
        account_id = None
        if zones:
            first_zone = list(zones.values())[0]
            account_id = first_zone.get("info", {}).get("account", {}).get("id")

        if not account_id:
            _LOGGER.error("No Account ID found to update registrar domain auto-renew")
            return

        await self.coordinator.client.update_registrar_domain(
            account_id, self._domain_name, enabled
        )
        await self.coordinator.async_request_refresh()

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


