"""Robomow3 — Home Assistant integration for Robomow robotic mowers."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RobomowClient
from .const import DOMAIN
from .coordinator import RobomowCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["lawn_mower", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Robomow3 from a config entry."""
    session = async_get_clientsession(hass)
    api = RobomowClient(session)

    await api.login(entry.data["email"], entry.data["password"])

    serial = entry.data["serial"]
    device_info = entry.data.get("device_info", {})

    coordinator = RobomowCoordinator(
        hass, api, serial, device_info_raw=device_info
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
