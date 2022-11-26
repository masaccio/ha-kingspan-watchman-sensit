# Base component constants
NAME = "Kingspan Connect Sensor"
DOMAIN = "kingspan_connect"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.1.0"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
ISSUE_URL = "https://github.com/masaccio/kingspan-connect-sensor/issues"

# Icons
ICON = "mdi:format-quote-close"

# Platforms
SENSOR = "sensor"
PLATFORMS = [SENSOR]

# Configuration and options
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Defaults
DEFAULT_NAME = DOMAIN

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This custom integration provides visibility of oil tank data from
Kingspan SENSiT sensors. Please raise any issues with this
integration here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
