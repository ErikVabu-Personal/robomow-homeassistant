"""Config flow for the Robomow3 integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RobomowAuthError, RobomowClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class RobomowConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Robomow3."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None
        self._devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._email = user_input["email"]
            self._password = user_input["password"]

            session = async_get_clientsession(self.hass)
            api = RobomowClient(session)
            try:
                await api.login(self._email, self._password)
                self._devices = await api.get_devices()
            except RobomowAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "cannot_connect"

            if not errors:
                if len(self._devices) == 1:
                    return self._create_entry(self._devices[0])
                if len(self._devices) > 1:
                    return await self.async_step_pick_device()
                errors["base"] = "no_devices"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("email"): str,
                vol.Required("password"): str,
            }),
            errors=errors,
        )

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        if user_input is not None:
            serial = user_input["device"]
            device = next(
                d for d in self._devices
                if d["serialNumber"] == serial
            )
            return self._create_entry(device)

        device_map = {
            d["serialNumber"]: (
                f"{d.get('customName') or d.get('modelDescription', '')} "
                f"({d['serialNumber']})"
            )
            for d in self._devices
        }
        return self.async_show_form(
            step_id="pick_device",
            data_schema=vol.Schema({
                vol.Required("device"): vol.In(device_map),
            }),
        )

    def _create_entry(self, device: dict[str, Any]) -> ConfigFlowResult:
        serial = device["serialNumber"]
        self._async_abort_entries_match({"serial": serial})
        return self.async_create_entry(
            title=device.get("customName") or serial,
            data={
                "email": self._email,
                "password": self._password,
                "serial": serial,
                "device_info": device,
            },
        )
