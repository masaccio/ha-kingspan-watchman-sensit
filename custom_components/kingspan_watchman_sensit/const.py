"""Constants for Kingspan Watchman SENSiT."""

# Base component constants
MANUFACTURER = "Kingspan"
MODEL = "Watchman SENSiT"
DOMAIN = "kingspan_watchman_sensit"
DOMAIN_DATA = f"{DOMAIN}_data"

ATTRIBUTION = "Data provided by https://www.connectsensor.com/"
ISSUE_URL = "https://github.com/masaccio/ha-kingspan-watchman-sensit/issues"

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
CONF_OIL_ENERGY_DENSITY = "oil_energy_density"

# Defaults
API_TIMEOUT = 30  # seconds
REFILL_THRESHOLD = 1.1  # factor considered a tank refill
DEFAULT_TANK_NAME = "My Tank"
DEFAULT_USAGE_WINDOW = 14  # days
DEFAULT_UPDATE_INTERVAL = 8  # hours
DEFAULT_OIL_ENERGY_DENSITY = 9.8  # kwH per litre
