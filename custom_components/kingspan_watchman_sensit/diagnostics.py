"""Diagnostics support for Kingspan Watchman SENSiT."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN

TO_REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    "serial_number",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is None:
        coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "config_entry_data": async_redact_data(entry.data, TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "tank_count": len(coordinator.data),
        "tanks": [
            {
                "level": tank.level,
                "serial_number": tank.serial_number,
                "model": tank.model,
                "name": tank.name,
                "capacity": tank.capacity,
                "last_read": tank.last_read,
                "history": tank.history,
                "usage_rate": tank.usage_rate,
                "forecast_empty": tank.forecast_empty,
            }
            for tank in coordinator.data
        ],
    }
