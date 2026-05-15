"""Async client for the Robomow3 cloud REST API.

Two backends:
  1. https://myrobomow.robomow.com/api  – authentication (v2/mobile/…)
  2. AWS API Gateway                    – device commands (api/V6/…)

Reverse-engineered from Robomow 3.0 APK v3.5.6.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    API_BRAND,
    AUTH_ENDPOINT,
    IOT_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)


class RobomowAuthError(Exception):
    """Login credentials rejected."""


class RobomowApiError(Exception):
    """Generic API failure (network / HTTP / parse)."""


class RobomowClient:
    """Thin async wrapper around the Robomow cloud API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._s = session
        self._email: str | None = None
        self._password: str | None = None
        self._access_token: str | None = None

    # ── Public properties ────────────────────────────────────────────────
    @property
    def access_token(self) -> str | None:
        return self._access_token

    # ── Auth ─────────────────────────────────────────────────────────
    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate and store the JWT for subsequent calls."""
        self._email = email
        self._password = password
        return await self._do_login()

    async def relogin(self) -> dict[str, Any]:
        """Re-authenticate using stored credentials."""
        if not (self._email and self._password):
            raise RobomowAuthError("relogin called without credentials")
        return await self._do_login()

    async def _do_login(self) -> dict[str, Any]:
        payload = {"email": self._email, "password": self._password}
        async with self._s.post(
            AUTH_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
        ) as resp:
            body = await resp.json(content_type=None)
            if resp.status in (401, 403):
                raise RobomowAuthError(
                    body.get("errorMessage", f"HTTP {resp.status}"))
            if resp.status != 200:
                raise RobomowApiError(f"Login HTTP {resp.status}")
            if not body.get("Success"):
                raise RobomowAuthError(
                    body.get("errorMessage", "Login failed"))

        self._access_token = body["AccessToken"]
        return body

    # ── V6 IoT API helpers ───────────────────────────────────────────────
    def _headers(self) -> dict[str, str]:
        if not self._access_token:
            raise RobomowAuthError("Not authenticated")
        return {
            "Authorization": self._access_token,
            "Content-Type": "application/json",
        }

    def _device_url(self, device_id: str, action: str) -> str:
        return (
            f"{IOT_BASE_URL}/api/V6/{API_BRAND}"
            f"/device/{device_id}/{action}"
        )

    async def _get(self, url: str) -> dict[str, Any]:
        async with self._s.get(url, headers=self._headers()) as resp:
            body = await resp.json(content_type=None)
            if resp.status == 401:
                # Token may have expired – try relogin once.
                await self.relogin()
                async with self._s.get(
                    url, headers=self._headers()
                ) as resp2:
                    body = await resp2.json(content_type=None)
                    resp2.raise_for_status()
                    return body
            resp.raise_for_status()
            return body

    async def _post(
        self, url: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        async with self._s.post(
            url, json=payload or {}, headers=self._headers()
        ) as resp:
            body = await resp.json(content_type=None)
            if resp.status == 401:
                await self.relogin()
                async with self._s.post(
                    url, json=payload or {}, headers=self._headers()
                ) as resp2:
                    body = await resp2.json(content_type=None)
                    resp2.raise_for_status()
                    return body
            resp.raise_for_status()
            return body

    # ── Customer / device listing ──────────────────────────────────────
    async def get_devices(self) -> list[dict[str, Any]]:
        url = f"{IOT_BASE_URL}/api/V6/{API_BRAND}/customer/get-devices"
        data = await self._get(url)
        return data.get("products", [])

    # ── Device endpoints ─────────────────────────────────────────────
    async def get_dashboard(self, device_id: str) -> dict[str, Any]:
        return await self._get(self._device_url(device_id, "get-dashboard"))

    async def get_robot_details(self, device_id: str) -> dict[str, Any]:
        return await self._get(
            self._device_url(device_id, "get-robot-details"))

    async def get_settings(self, device_id: str) -> dict[str, Any]:
        return await self._get(self._device_url(device_id, "get-settings"))

    async def get_on_connection_data(
        self, device_id: str
    ) -> dict[str, Any]:
        return await self._get(
            self._device_url(device_id, "get-on-connection-data"))

    async def get_scheduler(self, device_id: str) -> dict[str, Any]:
        return await self._get(self._device_url(device_id, "get-scheduler"))

    # ── Commands ─────────────────────────────────────────────────────
    async def start_mowing(
        self, device_id: str, zone: int = 0
    ) -> dict[str, Any]:
        return await self._post(
            self._device_url(device_id, "start-mowing"),
            {
                "zone": zone,
                "edge": False,
                "duration": "0",
                "returnToBase": False,
            },
        )

    async def stop_mowing(self, device_id: str) -> dict[str, Any]:
        return await self._post(
            self._device_url(device_id, "stop-mowing"))

    async def send_go_home(self, device_id: str) -> None:
        """Send the mower home (return to base).

        Uses the start-mowing REST endpoint with returnToBase=true.
        Reverse-engineered from StartMowingRequest in Robomow 3.0 APK:
        the same endpoint handles both mowing and return-to-base via
        the returnToBase boolean field.
        """
        _LOGGER.info("Sending return-to-base for %s", device_id)
        await self._post(
            self._device_url(device_id, "start-mowing"),
            {
                "zone": 0,
                "edge": False,
                "duration": "0",
                "returnToBase": True,
            },
        )
