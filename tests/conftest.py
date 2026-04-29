"""Pytest configuration and fixtures for the Cloudflare Advanced integration tests."""

import sys
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Attempt to mock Home Assistant if it is not installed
def mock_submodule(name):
    """Recursively mock submodules."""
    parts = name.split(".")
    for i in range(1, len(parts) + 1):
        full_name = ".".join(parts[:i])
        if full_name not in sys.modules:
            mock = MagicMock()
            sys.modules[full_name] = mock
            if i > 1:
                parent_name = ".".join(parts[: i - 1])
                setattr(sys.modules[parent_name], parts[i - 1], mock)


@dataclass(frozen=True, kw_only=True)
class MockEntityDescription:
    """Base class for mocked entity descriptions."""

    key: str
    name: str | None = None
    icon: str | None = None
    entity_category: Any | None = None
    entity_registry_enabled_default: bool = True
    translation_key: str | None = None
    translation_placeholders: dict[str, str] | None = None
    native_unit_of_measurement: str | None = None
    device_class: Any | None = None
    state_class: Any | None = None
    options: list[str] | None = None


class MockEntity:
    """Base class for mocked entities."""

    _attr_has_entity_name: bool = False
    _attr_unique_id: str | None = None
    _attr_name: str | None = None
    _attr_device_info: Any | None = None
    _attr_extra_state_attributes: dict[str, Any] | None = None

    def async_write_ha_state(self):
        pass


class MockCoordinatorEntity(MockEntity):
    """Base class for mocked coordinator entities."""

    def __init__(self, coordinator, *args, **kwargs):
        self.coordinator = coordinator


# Pre-populate sys.modules
platforms = ["sensor", "binary_sensor", "switch", "select", "button"]
for platform in platforms:
    module_name = f"homeassistant.components.{platform}"
    mock_module = MagicMock()
    ent_class_name = "".join([n.capitalize() for n in platform.split("_")]) + "Entity"
    desc_class_name = (
        "".join([n.capitalize() for n in platform.split("_")]) + "EntityDescription"
    )
    setattr(mock_module, ent_class_name, MockEntity)
    setattr(mock_module, desc_class_name, MockEntityDescription)
    sys.modules[module_name] = mock_module

sys.modules["homeassistant.exceptions"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.entity"] = MagicMock()


class MockDataUpdateCoordinator:
    def __init__(self, *args, **kwargs):
        self.data = {}

    async def async_config_entry_first_refresh(self):
        pass

    def __class_getitem__(cls, _):
        return cls


sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()
sys.modules[
    "homeassistant.helpers.update_coordinator"
].CoordinatorEntity = MockCoordinatorEntity
sys.modules[
    "homeassistant.helpers.update_coordinator"
].DataUpdateCoordinator = MockDataUpdateCoordinator


class MockConfigFlow:
    async def async_set_unique_id(self, unique_id, *, raise_on_progress=True):
        pass

    def _abort_if_unique_id_configured(self, *args, **kwargs):
        pass

    def async_show_form(self, *args, **kwargs):
        return {"type": "form", "step_id": kwargs.get("step_id")}

    def async_create_entry(self, *args, **kwargs):
        return {
            "type": "create_entry",
            "title": kwargs.get("title"),
            "data": kwargs.get("data"),
        }


sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.config_entries"].ConfigFlow = MockConfigFlow

ha_mocks = [
    "homeassistant.core",
    "homeassistant.helpers.aiohttp_client",
    "homeassistant.helpers.config_validation",
    "homeassistant.helpers.entity_platform",
    "homeassistant.data_entry_flow",
    "homeassistant.helpers.selector",
]
for mock_name in ha_mocks:
    mock_submodule(mock_name)


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.cloudflare_advanced.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_api_client() -> Generator[AsyncMock]:
    """Mock the CloudflareApiClient."""
    with patch(
        "custom_components.cloudflare_advanced.api.CloudflareApiClient", autospec=True
    ) as mock_client:
        client = mock_client.return_value
        client.verify_auth = AsyncMock(return_value=True)
        client.get_zones = AsyncMock(
            return_value=[{"id": "zone_id", "name": "example.com"}]
        )
        client.get_zone_settings = AsyncMock(
            return_value=[{"id": "development_mode", "value": "off"}]
        )
        client.get_dns_records = AsyncMock(return_value=[])
        client.get_analytics = AsyncMock(return_value={})
        client.get_tunnels = AsyncMock(return_value=[])
        client.get_pages_projects = AsyncMock(return_value=[])
        client.get_certificate_packs = AsyncMock(return_value=[])
        client.get_accounts = AsyncMock(return_value=[{"id": "account_id"}])
        client.get_email_routing_rules = AsyncMock(return_value=[])
        client.update_email_routing_rule = AsyncMock(return_value={})
        client.get_gateway_rules = AsyncMock(return_value=[])
        client.update_gateway_rule = AsyncMock(return_value={})
        client.get_load_balancer_pools = AsyncMock(return_value=[])
        client.get_zone_rulesets = AsyncMock(return_value=[])
        client.get_zone_ruleset_rules = AsyncMock(return_value=[])
        client.update_zone_ruleset_rule = AsyncMock(return_value={})
        client.get_registrar_domains = AsyncMock(return_value=[])
        client.get_images_stats = AsyncMock(return_value={})
        client.update_registrar_domain = AsyncMock(return_value={})
        yield client



@pytest.fixture
def hass() -> MagicMock:
    """Mock HomeAssistant."""
    mock_hass = MagicMock()
    mock_hass.data = {}
    mock_hass.services = MagicMock()

    from unittest.mock import AsyncMock

    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    return mock_hass
