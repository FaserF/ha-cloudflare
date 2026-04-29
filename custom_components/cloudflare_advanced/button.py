"""Button platform for Cloudflare Advanced."""

from __future__ import annotations


from homeassistant.components.button import ButtonEntity
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
    """Set up the button platform."""
    coordinator: CloudflareAdvancedCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = []

    for zone_id, zone_data in coordinator.data.get("zones", {}).items():
        zone_name = zone_data["info"]["name"]
        entities.append(CloudflarePurgeCacheButton(coordinator, zone_id, zone_name))

    async_add_entities(entities)


class CloudflarePurgeCacheButton(
    CoordinatorEntity[CloudflareAdvancedCoordinator], ButtonEntity
):
    """Button to purge all cache for a Cloudflare Zone."""

    def __init__(
        self,
        coordinator: CloudflareAdvancedCoordinator,
        zone_id: str,
        zone_name: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._attr_unique_id = f"{zone_id}_purge_cache_button"
        self._attr_translation_key = "purge_cache"
        self._attr_has_entity_name = True

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.client.purge_cache(self._zone_id, purge_everything=True)

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
