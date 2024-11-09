"""Constants for Kingspan Watchman SENSiT."""

# Base component constants
NAME = "Kingspan Watchman SENSiT"
DOMAIN = "kingspan_watchman_sensit"
DOMAIN_DATA = f"{DOMAIN}_data"

ATTRIBUTION = "Data provided by https://www.connectsensor.com/"
ISSUE_URL = "https://github.com/masaccio/ha-kingspan-watchman-sensit/issues"

ENERGY_DENSITY_KWH_PER_LITER = 10.35

# Platforms
SENSOR = "sensor"
PLATFORMS = [SENSOR]

# Configuration and options
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_NAME = "name"
CONF_USAGE_WINDOW = "usage_window"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_KINGSPAN_DEBUG = "debug_kingspan"

# Defaults
DEFAULT_TANK_NAME = "My Tank"
API_TIMEOUT = 30  # seconds
REFILL_THRESHOLD = 1.1  # factor considerd a tank refill
DEFAULT_USAGE_WINDOW = 14  # days
DEFAULT_UPDATE_INTERVAL = 8  # hours
