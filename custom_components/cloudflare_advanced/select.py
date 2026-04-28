"""Select platform for Cloudflare Advanced."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
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
    """Set up the select platform."""
    coordinator: CloudflareAdvancedCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []

    for zone_id, zone_data in coordinator.data.get("zones", {}).items():
        zone_name = zone_data["info"]["name"]
        entities.append(
            CloudflareSettingSelect(
                coordinator,
                zone_id,
                zone_name,
                "security_level",
                "Security Level",
                ["off", "essentially_off", "low", "medium", "high", "under_attack"],
            )
        )

    async_add_entities(entities)


class CloudflareSettingSelect(
    CoordinatorEntity[CloudflareAdvancedCoordinator], SelectEntity
):
    """Select entity for Cloudflare Zone settings."""

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        zone_id: str,
        zone_name: str,
        setting_id: str,
        setting_label: str,
        options: list[str],
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._setting_id = setting_id
        self._attr_unique_id = f"{zone_id}_{setting_id}_select"
        self._attr_options = options
        self._attr_translation_key = setting_id
        self._attr_has_entity_name = True

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        zone_data = self.coordinator.data.get("zones", {}).get(self._zone_id, {})
        settings = zone_data.get("settings", [])

        for setting in settings:
            if setting.get("id") == self._setting_id:
                val = setting.get("value")
                if val in self._attr_options:
                    return val
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.client.update_zone_setting(
            self._zone_id, self._setting_id, option
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
