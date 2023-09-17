"""Test Kingspan Watchman SENSiT setup process."""
import pytest

from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryAuthFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kingspan_watchman_sensit import (
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
    SENSiTDataUpdateCoordinator,
)
from custom_components.kingspan_watchman_sensit.const import DOMAIN
from .const import MOCK_CONFIG


async def test_refresh_data(hass, mock_sensor_client, caplog):
    """Test state refresh through the API"""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert type(hass.data[DOMAIN][config_entry.entry_id]) == SENSiTDataUpdateCoordinator

    # Check that the API is called to update data twice for two calls
    # to HASS's data update method
    caplog.clear()
    await hass.data[DOMAIN][config_entry.entry_id]._async_update_data()
    await hass.data[DOMAIN][config_entry.entry_id]._async_update_data()
    update_logs = [
        log[2] for log in caplog.record_tuples if "Fetching tank data" in log[2]
    ]
    assert len(update_logs) == 2

    assert await async_unload_entry(hass, config_entry)


async def test_setup_unload_and_reload_entry(hass, bypass_get_data):
    """Test entry setup and unload."""
    # Create a mock entry so we don't have to go through config flow
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

    # Set up the entry and assert that the values set during setup are where we expect
    # them to be. Because we have patched the SENSiTDataUpdateCoordinator.async_get_data
    # call, no code from custom_components/kingspan_watchman_sensit/api.py actually runs.
    assert await async_setup_entry(hass, config_entry)
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert type(hass.data[DOMAIN][config_entry.entry_id]) == SENSiTDataUpdateCoordinator

    # Reload the entry and assert that the data from above is still there
    assert await async_reload_entry(hass, config_entry) is None
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert type(hass.data[DOMAIN][config_entry.entry_id]) == SENSiTDataUpdateCoordinator

    # Unload the entry and verify that the data has been removed
    assert await async_unload_entry(hass, config_entry)
    assert config_entry.entry_id not in hass.data[DOMAIN]


async def test_setup_entry_exception(hass, error_on_get_data):
    """Test ConfigEntryNotReady when API raises an exception during entry setup."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

    # In this case we are testing the condition where async_setup_entry raises
    # ConfigEntryNotReady using the `error_on_get_data` fixture which simulates
    # an error.
    with pytest.raises(ConfigEntryNotReady):
        assert await async_setup_entry(hass, config_entry)


async def test_auth_errors(hass, bypass_get_data):
    """Test entry setup and unload."""
    # Create a mock entry so we don't have to go through config flow
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={"username": None}, entry_id="test"
    )

    with pytest.raises(ConfigEntryAuthFailed):
        assert await async_setup_entry(hass, config_entry)

    assert DOMAIN in hass.data and config_entry.entry_id not in hass.data[DOMAIN]


async def test_auth_exception(hass, error_sensor_client):
    """Test entry setup and unload."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

    with pytest.raises(ConfigEntryAuthFailed) as e:
        assert await async_setup_entry(hass, config_entry)
    assert "Credentials invalid" in str(e)


async def test_auth_timeout(hass, timeout_sensor_client):
    """Test entry setup and unload."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

    with pytest.raises(ConfigEntryNotReady) as e:
        assert await async_setup_entry(hass, config_entry)
    assert "Timed out while connecting to Kingspan service" in str(e)
