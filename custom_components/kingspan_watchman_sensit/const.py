"""Constants for Kingspan Watchman SENSiT."""
# Base component constants
NAME = "Kingspan Watchman SENSiT"
DOMAIN = "kingspan_watchman_sensit"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.7"

ATTRIBUTION = "Data provided by https://www.connectsensor.com/"
ISSUE_URL = "https://github.com/masaccio/ha-kingspan-watchman-sensit/issues"

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
UPDATE_INTERVAL_HOURS = 8
