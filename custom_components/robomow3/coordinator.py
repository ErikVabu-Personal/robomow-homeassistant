"""DataUpdateCoordinator for polling the Robomow cloud API."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import RobomowApiError, RobomowAuthError, RobomowClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, STATE_MAP, BATTERY_STATE_MAP

_LOGGER = logging.getLogger(__name__)


class RobomowCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the Robomow cloud and merge dashboard + settings into one dict."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: RobomowClient,
        serial: str,
        device_info_raw: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{serial}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.serial = serial
        self.device_info_raw = device_info_raw or {}
        self._conn_data: dict[str, Any] | None = None

    # ── Polling ──────────────────────────────────────────────────────────

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            dashboard = await self.api.get_dashboard(self.serial)
        except RobomowAuthError as err:
            raise UpdateFailed(f"Auth error: {err}") from err
        except Exception as err:
            _LOGGER.debug("Dashboard fetch failed: %s", err)
            dashboard = (self.data or {}).get("dashboard") or {}

        try:
            settings = await self.api.get_settings(self.serial)
        except Exception as err:
            _LOGGER.debug("Settings fetch failed: %s", err)
            settings = (self.data or {}).get("settings") or {}

        # Fetch connection data once (static info like firmware).
        if self._conn_data is None:
            try:
                self._conn_data = await self.api.get_on_connection_data(
                    self.serial
                )
            except Exception as err:
                _LOGGER.debug("Connection data fetch failed: %s", err)
                self._conn_data = {}

        # Never store None — always store dicts so accessors don't crash.
        return {
            "dashboard": dashboard if isinstance(dashboard, dict) else {},
            "settings": settings if isinstance(settings, dict) else {},
            "connection": self._conn_data or {},
        }

    # ── Convenience accessors ────────────────────────────────────────────

    def _dash(self) -> dict[str, Any]:
        return (self.data or {}).get("dashboard") or {}

    def _settings(self) -> dict[str, Any]:
        return (self.data or {}).get("settings") or {}

    def _conn(self) -> dict[str, Any]:
        return (self.data or {}).get("connection") or {}

    # State
    def get_state_raw(self) -> int | None:
        return self._dash().get("state")

    def get_state_name(self) -> str:
        raw = self.get_state_raw()
        return STATE_MAP.get(raw, f"unknown ({raw})") if raw is not None else "unknown"

    # Battery (from dashboard → batteryInfo)
    def get_battery_percent(self) -> int | None:
        bi = self._dash().get("batteryInfo") or {}
        return bi.get("percent")

    def get_battery_state(self) -> str | None:
        bi = self._dash().get("batteryInfo") or {}
        raw = bi.get("state")
        return BATTERY_STATE_MAP.get(raw) if raw is not None else None

    # Operations
    def get_current_operation(self) -> dict[str, Any]:
        ops = self._dash().get("operations", {})
        return ops.get("currentOperation", {})

    def get_previous_operation(self) -> dict[str, Any]:
        ops = self._dash().get("operations", {})
        return ops.get("previousOperation", {})

    def get_next_operation(self) -> dict[str, Any]:
        ops = self._dash().get("operations", {})
        return ops.get("nextOperation", {})

    # WiFi (lives in settings response, not dashboard)
    def get_wifi_rssi(self) -> int | None:
        wi = self._settings().get("wifiInfo") or {}
        return wi.get("rssi")

    def get_wifi_network(self) -> str | None:
        wi = self._settings().get("wifiInfo") or {}
        return wi.get("networkName")

    # Settings
    def get_edge_mode(self) -> bool | None:
        s = self._settings().get("settings") or {}
        return s.get("edgeMode")

    def get_child_lock(self) -> bool | None:
        s = self._settings().get("settings") or {}
        cl = s.get("childLock") or {}
        return cl.get("enable")

    def get_scheduler_on(self) -> bool | None:
        s = self._settings().get("settings", {})
        # This comes from get-robot-details, but we can derive it
        return None  # Fetched separately if needed

    # Connection / firmware
    def get_model_name(self) -> str:
        return (
            self._conn().get("modelName")
            or self.device_info_raw.get("modelDescription")
            or "Robomow"
        )

    def get_platform(self) -> str | None:
        return self._conn().get("platform")

    def get_device_connected(self) -> bool | None:
        return self._conn().get("deviceConnectedToAws")

    def get_device_turned_on(self) -> bool | None:
        return self._conn().get("deviceTurnedOn")

    def get_device_last_seen(self) -> str | None:
        return self._conn().get("deviceLastSeen")

    def get_firmware(self) -> str | None:
        sv = self._conn().get("deviceSoftwareVersion") or {}
        if not sv:
            return None
        return f"{sv.get('controllerMain', '?')}.{sv.get('controllerTest', '?')}"

    # Zone info
    def _main_zone(self) -> dict[str, Any]:
        rz = self._dash().get("robotZones") or {}
        return rz.get("mainZoneSettings") or {}

    def get_main_zone_mow_time(self) -> str | None:
        return self._main_zone().get("mowTime")

    def get_main_zone_debt(self) -> str | None:
        return self._main_zone().get("debt")

    def get_main_zone_mowing_time_required(self) -> str | None:
        return self._main_zone().get("mowingTimeRequired")

    def get_main_zone_mow_complete(self) -> bool | None:
        return self._main_zone().get("mowTimeComplete")

    # Operations — extended details
    def get_prev_op_start(self) -> str | None:
        return self.get_previous_operation().get("startOperationDate")

    def get_prev_op_end(self) -> str | None:
        return self.get_previous_operation().get("endDate")

    def get_prev_op_duration(self) -> str | None:
        return self.get_previous_operation().get("operationDuration")

    def get_prev_op_mowing_duration(self) -> str | None:
        return self.get_previous_operation().get("mowingDuration")

    def get_current_op_start(self) -> str | None:
        return self.get_current_operation().get("startOperationDate")

    def get_current_op_duration(self) -> str | None:
        return self.get_current_operation().get("operationDuration")

    def get_next_op_start(self) -> str | None:
        return self.get_next_operation().get("startOperationDate")

    # Settings — additional fields
    def get_audio_on(self) -> bool | None:
        s = self._settings().get("settings") or {}
        return s.get("audioOn")

    def get_anti_theft_enabled(self) -> bool | None:
        s = self._settings().get("settings") or {}
        at = s.get("antiTheft") or {}
        return at.get("enable")

    def get_eco_mode(self) -> bool | None:
        s = self._settings().get("settings") or {}
        eco = s.get("systemEconomicMode") or {}
        return eco.get("enable")

    def get_eco_mode_active(self) -> bool | None:
        s = self._settings().get("settings") or {}
        eco = s.get("systemEconomicMode") or {}
        return eco.get("active")

    def get_wifi_connection_status(self) -> int | None:
        wi = self._settings().get("wifiInfo") or {}
        return wi.get("connectionStatus")

    # Connection — extended details
    def get_platform_type(self) -> str | None:
        return self._conn().get("platformType")

    def get_brand(self) -> str | None:
        return self._conn().get("brand")

    def get_robot_serial(self) -> str | None:
        return self._conn().get("robotSerialNumber")

    def get_firmware_full(self) -> str | None:
        """Full firmware string with controller, monitor, UI, BLE, and WiFi."""
        sv = self._conn().get("deviceSoftwareVersion") or {}
        if not sv:
            return None
        parts = []
        cm = sv.get("controllerMain")
        ct = sv.get("controllerTest")
        if cm is not None:
            parts.append(f"ctrl:{cm}.{ct or 0}")
        mm = sv.get("monitorMain")
        mt = sv.get("monitorTest")
        if mm is not None:
            parts.append(f"mon:{mm}.{mt or 0}")
        um = sv.get("uiMain")
        ut = sv.get("uiTest")
        if um is not None:
            parts.append(f"ui:{um}.{ut or 0}")
        ble = sv.get("bleVersion")
        if ble is not None:
            parts.append(f"ble:{ble}")
        wm = sv.get("wifiMajor")
        wn = sv.get("wifiMinor")
        if wm is not None:
            parts.append(f"wifi:{wm}.{wn or 0}")
        return " / ".join(parts) if parts else None

    def get_hardware_version(self) -> int | None:
        sv = self._conn().get("deviceSoftwareVersion") or {}
        return sv.get("hardwareVersion")

    # System failure / safety
    def get_system_failure_id(self) -> int | None:
        sf = self._dash().get("systemFailure") or {}
        return sf.get("id")

    def get_user_message_id(self) -> int | None:
        um = self._dash().get("userMessage") or {}
        return um.get("id")

    # ── Commands ───────────────────────────────────────────────────────

    async def async_start_mowing(self, zone: int = 0) -> None:
        await self.api.start_mowing(self.serial, zone=zone)
        await self.async_request_refresh()

    async def async_stop_mowing(self) -> None:
        await self.api.stop_mowing(self.serial)
        await self.async_request_refresh()

    async def async_go_home(self) -> None:
        """Send the mower home (return to base).

        Uses the start-mowing endpoint with returnToBase=true,
        as discovered from the Robomow APK's StartMowingRequest model.
        """
        await self.api.send_go_home(self.serial)
        await self.async_request_refresh()
