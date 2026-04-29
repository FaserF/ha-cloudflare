"""Constants for the Cloudflare Advanced integration."""

DOMAIN = "cloudflare_advanced"

CONF_API_TOKEN = "api_token"
CONF_EMAIL = "email"
CONF_API_KEY = "api_key"
CONF_ZONES = "zones"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ENABLE_DDNS = "enable_ddns"

API_URL = "https://api.cloudflare.com/client/v4"
GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"

PLATFORMS = ["sensor", "binary_sensor", "switch", "select", "button"]
