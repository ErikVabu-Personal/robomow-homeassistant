"""LawnMowerEntity for Robomow mowers."""

from __future__ import annotations

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import RobomowCoordinator

# Map Robomow dashboard state → HA LawnMowerActivity
_ACTIVITY_MAP = {
    "idle": LawnMowerActivity.DOCKED,
    "charging": LawnMowerActivity.DOCKED,
    "in_base": LawnMowerActivity.DOCKED,
    "mowing": LawnMowerActivity.MOWING,
    "going_home": LawnMowerActivity.MOWING,
    "edge": LawnMowerActivity.MOWING,
    "error": LawnMowerActivity.ERROR,
    "paused": LawnMowerActivity.PAUSED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
    if coordinator is None:
        return
    async_add_entities([RobomowLawnMower(coordinator)])


class RobomowLawnMower(
    CoordinatorEntity[RobomowCoordinator], LawnMowerEntity
):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        LawnMowerEntityFeature.START_MOWING
        | LawnMowerEntityFeature.PAUSE
        | LawnMowerEntityFeature.DOCK
    )

    def __init__(self, coordinator: RobomowCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial}_lawn_mower"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.serial)},
            "manufacturer": MANUFACTURER,
            "model": coordinator.get_model_name(),
            "name": (
                coordinator.device_info_raw.get("customName")
                or f"Robomow {coordinator.serial}"
            ),
            "serial_number": coordinator.serial,
            "sw_version": coordinator.get_firmware(),
        }

    @property
    def activity(self) -> LawnMowerActivity | None:
        state = self.coordinator.get_state_name()
        return _ACTIVITY_MAP.get(state)

    @property
    def extra_state_attributes(self) -> dict:
        c = self.coordinator
        attrs: dict = {
            "robomow_state": c.get_state_name(),
            "battery_percent": c.get_battery_percent(),
            "battery_state": c.get_battery_state(),
        }
        cur = c.get_current_operation()
        if cur:
            attrs["current_operation_start"] = cur.get(
                "startOperationDate"
            )
            attrs["current_operation_duration"] = cur.get(
                "operationDuration"
            )
        prev = c.get_previous_operation()
        if prev:
            attrs["previous_operation_end"] = prev.get("endDate")
            attrs["previous_operation_duration"] = prev.get(
                "operationDuration"
            )
        nxt = c.get_next_operation()
        if nxt:
            attrs["next_operation"] = nxt.get("startOperationDate")

        attrs["mow_time"] = c.get_main_zone_mow_time()
        attrs["mow_debt"] = c.get_main_zone_debt()
        attrs["device_last_seen"] = c.get_device_last_seen()
        return attrs

    async def async_start_mowing(self) -> None:
        await self.coordinator.async_start_mowing()

    async def async_dock(self) -> None:
        """Send the mower home (return to base) via AWS IoT Shadow."""
        await self.coordinator.async_go_home()

    async def async_pause(self) -> None:
        """Pause / stop the mower in place."""
        await self.coordinator.async_stop_mowing()
