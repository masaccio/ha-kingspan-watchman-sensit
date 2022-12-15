"""Constants for Kingspan Watchman SENSiT tests."""

from enum import Enum
from custom_components.kingspan_watchman_sensit.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
)

MOCK_CONFIG = {CONF_USERNAME: "test@example.com", CONF_PASSWORD: "s3cret"}

MOCK_GET_DATA_METHOD = (
    "custom_components.kingspan_watchman_sensit.SENSiTApiClient._get_tank_data"
)

# Mock tank data to readings
MOCK_TANK_LEVEL = 1000
MOCK_TANK_SERIAL_NUMBER = "20001234"
MOCK_TANK_MODEL = "Acme Tank"
MOCK_TANK_NAME = "Tanky McTankFace"
MOCK_TANK_CAPACITY = 2000


class HistoryType(Enum):
    DECREASING = 0
    NONE = 1
    EXPIRED = 2
