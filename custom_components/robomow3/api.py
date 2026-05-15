"""Async client for the Robomow3 cloud REST API.

Three backends:
  1. https://myrobomow.robomow.com/api  – authentication (v2/mobile/…)
  2. AWS API Gateway                    – device commands (api/V6/…)
  3. AWS IoT Device Shadow (REST)       – go-home command (mutual-TLS)

Reverse-engineered from Robomow 3.0 APK v3.5.6.
"""

from __future__ import annotations

import json
import logging
import ssl
import tempfile
from pathlib import Path
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

    # ── Public properties ────────────────────────────────────────────
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

    # ── V6 IoT API helpers ───────────────────────────────────────────
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

    # ── Customer / device listing ────────────────────────────────────
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
            {"zone": zone},
        )

    async def stop_mowing(self, device_id: str) -> dict[str, Any]:
        return await self._post(
            self._device_url(device_id, "stop-mowing"))

    # ── Go-home via AWS IoT MQTT Shadow ────────────────────────────

    async def get_client_certificate_pfx(
        self, device_id: str
    ) -> bytes:
        """Fetch the PFX client certificate for AWS IoT mutual-TLS."""
        url = self._device_url(device_id, "get-client-certificate-pfx")
        async with self._s.get(url, headers=self._headers()) as resp:
            if resp.status == 401:
                await self.relogin()
                async with self._s.get(
                    url, headers=self._headers()
                ) as resp2:
                    resp2.raise_for_status()
                    return await resp2.read()
            resp.raise_for_status()
            return await resp.read()

    def _parse_pfx(self, pfx_raw: bytes, device_id: str) -> bytes:
        """Extract raw PFX bytes from the API response (JSON envelope)."""
        import base64

        try:
            envelope = json.loads(pfx_raw)
            for key in ("file", "pfx", "certificate", "data", "body"):
                if key in envelope:
                    return base64.b64decode(envelope[key])
            return base64.b64decode(envelope)
        except (json.JSONDecodeError, TypeError, ValueError):
            return pfx_raw

    def _build_ssl_context(
        self, pfx_data: bytes, device_id: str
    ) -> ssl.SSLContext:
        """Parse PFX and build an SSL context for mutual-TLS.

        The PFX password is the device serial number.
        """
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            NoEncryption,
            PrivateFormat,
            pkcs12,
        )

        try:
            private_key, certificate, chain = (
                pkcs12.load_key_and_certificates(
                    pfx_data, device_id.encode()
                )
            )
        except Exception as err:
            raise RobomowApiError(
                f"Cannot parse PFX certificate: {err}"
            ) from err

        if private_key is None or certificate is None:
            raise RobomowApiError("PFX missing key or certificate")

        # Write PEM files to temp dir
        tmp = Path(tempfile.mkdtemp(prefix="robomow_"))
        cert_path = tmp / "cert.pem"
        key_path = tmp / "key.pem"

        cert_pem = certificate.public_bytes(Encoding.PEM)
        if chain:
            for ca in chain:
                cert_pem += ca.public_bytes(Encoding.PEM)
        cert_path.write_bytes(cert_pem)

        key_path.write_bytes(
            private_key.private_bytes(
                Encoding.PEM,
                PrivateFormat.TraditionalOpenSSL,
                NoEncryption(),
            )
        )

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_cert_chain(str(cert_path), str(key_path))
        ctx.load_default_certs()

        # Cleanup temp files
        cert_path.unlink(missing_ok=True)
        key_path.unlink(missing_ok=True)
        tmp.rmdir()

        return ctx

    @staticmethod
    def _make_mqtt_client(client_id: str):
        """Create paho MQTT client (compatible with v1 and v2 API)."""
        import paho.mqtt.client as mqtt

        try:
            return mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_id,
            )
        except (AttributeError, TypeError):
            return mqtt.Client(client_id=client_id)

    async def send_go_home(self, device_id: str) -> None:
        """Send 'return to base' via AWS IoT MQTT shadow update.

        The go-home command is not available via REST. The Robomow app
        publishes a shadow update over MQTT (port 8883) with mutual-TLS
        client certs.  We do the same here using paho-mqtt.
        """
        _LOGGER.debug("Fetching PFX certificate for %s", device_id)
        pfx_raw = await self.get_client_certificate_pfx(device_id)
        pfx_data = self._parse_pfx(pfx_raw, device_id)
        ssl_ctx = self._build_ssl_context(pfx_data, device_id)

        shadow_topic = f"$aws/things/{device_id}/shadow/update"
        accepted_topic = f"$aws/things/{device_id}/shadow/update/accepted"
        rejected_topic = f"$aws/things/{device_id}/shadow/update/rejected"

        payload = json.dumps({
            "state": {"desired": {"returnToBase": True}}
        })

        result: dict[str, Any] = {"done": False, "error": None}

        def on_connect(client, userdata, flags, *args):
            rc = args[0] if args else 0
            rc_val = int(rc) if hasattr(rc, "value") else rc
            if rc_val != 0:
                result["error"] = f"MQTT connect failed: rc={rc}"
                result["done"] = True
                return
            _LOGGER.debug("MQTT connected to AWS IoT")
            client.subscribe(accepted_topic)
            client.subscribe(rejected_topic)
            client.publish(shadow_topic, payload)
            _LOGGER.debug("Published returnToBase to %s", shadow_topic)

        def on_message(client, userdata, msg):
            _LOGGER.debug("MQTT %s: %s", msg.topic, msg.payload[:300])
            if "rejected" in msg.topic:
                result["error"] = msg.payload.decode(errors="replace")[:200]
            result["done"] = True
            client.disconnect()

        # Run the synchronous paho-mqtt client in the executor
        def _mqtt_publish():
            import time
            from .const import IOT_SHADOW_HOST

            # AWS IoT policy requires client_id = thing name
            client = self._make_mqtt_client(device_id)
            client.tls_set_context(ssl_ctx)
            client.on_connect = on_connect
            client.on_message = on_message

            client.connect(IOT_SHADOW_HOST, 8883, keepalive=30)

            deadline = time.time() + 15
            while not result["done"] and time.time() < deadline:
                client.loop(timeout=0.5)

            if not result["done"]:
                result["error"] = "MQTT shadow update timed out"
                try:
                    client.disconnect()
                except Exception:
                    pass

        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _mqtt_publish)

        if result.get("error"):
            raise RobomowApiError(
                f"Go-home failed: {result['error']}"
            )
