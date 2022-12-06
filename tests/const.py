"""Constants for kingspan_connect tests."""
from custom_components.kingspan_connect.const import CONF_PASSWORD, CONF_USERNAME
from datetime import datetime

# Mock config data to be used across multiple tests
MOCK_CONFIG = {CONF_USERNAME: "test@example.com", CONF_PASSWORD: "s3cret"}

# Mock tank data to readings
MOCK_TANK_LEVEL = 1000
MOCK_TANK_SERIAL_NUMBER = "20001234"
MOCK_TANK_MODEL = "Acme Tank"
MOCK_TANK_NAME = "Tanky McTankFace"
MOCK_TANK_CAPACITY = 2000
MOCK_TANK_LAST_READ = datetime(2020, 6, 30, 0, 10, 0)
