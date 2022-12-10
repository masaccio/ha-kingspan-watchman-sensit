"""Constants for Watchman SENSiT."""
# Base component constants
NAME = "Watchman SENSiT"
DOMAIN = "kingspan_watchman_sensit"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.1.0"

ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
ISSUE_URL = "https://github.com/masaccio/ha-kingspan-watchman-sensit/issues"

# Icons
ICON = "mdi:gauge"

# Platforms
SENSOR = "sensor"
PLATFORMS = [SENSOR]


# Configuration and options
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Defaults
DEFAULT_NAME = DOMAIN
API_TIMEOUT = 30

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
