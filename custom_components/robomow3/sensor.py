"""Sensor entities for the Robomow3 integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, SIGNAL_STRENGTH_DECIBELS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import RobomowCoordinator


@dataclass(kw_only=True, frozen=True)
class RobomowSensorDescription(SensorEntityDescription):
    value_fn: Callable[[RobomowCoordinator], float | int | str | None]


# ── Core sensors ──────────────────────────────────────────────────────

_CORE_SENSORS: tuple[RobomowSensorDescription, ...] = (
    RobomowSensorDescription(
        key="state",
        translation_key="mower_state",
        name="State",
        icon="mdi:robot-mower",
        value_fn=lambda c: c.get_state_name(),
    ),
    RobomowSensorDescription(
        key="battery_percent",
        translation_key="battery_percent",
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda c: c.get_battery_percent(),
    ),
    RobomowSensorDescription(
        key="battery_state",
        translation_key="battery_state",
        name="Battery state",
        icon="mdi:battery",
        value_fn=lambda c: c.get_battery_state(),
    ),
)

# ── WiFi sensors ──────────────────────────────────────────────────────

_WIFI_SENSORS: tuple[RobomowSensorDescription, ...] = (
    RobomowSensorDescription(
        key="wifi_rssi",
        translation_key="wifi_rssi",
        name="WiFi signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_wifi_rssi(),
    ),
    RobomowSensorDescription(
        key="wifi_network",
        translation_key="wifi_network",
        name="WiFi network",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_wifi_network(),
    ),
)

# ── Operation sensors ─────────────────────────────────────────────────

_OPERATION_SENSORS: tuple[RobomowSensorDescription, ...] = (
    RobomowSensorDescription(
        key="next_mowing",
        translation_key="next_mowing",
        name="Next mowing",
        icon="mdi:calendar-clock",
        value_fn=lambda c: c.get_next_op_start(),
    ),
    RobomowSensorDescription(
        key="current_op_start",
        translation_key="current_op_start",
        name="Current operation start",
        icon="mdi:clock-start",
        value_fn=lambda c: c.get_current_op_start(),
    ),
    RobomowSensorDescription(
        key="current_op_duration",
        translation_key="current_op_duration",
        name="Current operation duration",
        icon="mdi:timer-outline",
        value_fn=lambda c: c.get_current_op_duration(),
    ),
    RobomowSensorDescription(
        key="prev_op_start",
        translation_key="prev_op_start",
        name="Previous operation start",
        icon="mdi:clock-start",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_prev_op_start(),
    ),
    RobomowSensorDescription(
        key="prev_op_end",
        translation_key="prev_op_end",
        name="Previous operation end",
        icon="mdi:clock-end",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_prev_op_end(),
    ),
    RobomowSensorDescription(
        key="prev_op_duration",
        translation_key="prev_op_duration",
        name="Previous operation duration",
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_prev_op_duration(),
    ),
    RobomowSensorDescription(
        key="prev_op_mowing_duration",
        translation_key="prev_op_mowing_duration",
        name="Previous mowing duration",
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_prev_op_mowing_duration(),
    ),
)

# ── Zone sensors ──────────────────────────────────────────────────────

_ZONE_SENSORS: tuple[RobomowSensorDescription, ...] = (
    RobomowSensorDescription(
        key="mow_time",
        translation_key="mow_time",
        name="Mow time",
        icon="mdi:timer-outline",
        value_fn=lambda c: c.get_main_zone_mow_time(),
    ),
    RobomowSensorDescription(
        key="mow_debt",
        translation_key="mow_debt",
        name="Mow debt",
        icon="mdi:timer-alert-outline",
        value_fn=lambda c: c.get_main_zone_debt(),
    ),
    RobomowSensorDescription(
        key="mow_time_required",
        translation_key="mow_time_required",
        name="Mow time required",
        icon="mdi:timer-sand",
        value_fn=lambda c: c.get_main_zone_mowing_time_required(),
    ),
)

# ── Settings sensors ──────────────────────────────────────────────────

_SETTINGS_SENSORS: tuple[RobomowSensorDescription, ...] = (
    RobomowSensorDescription(
        key="edge_mode",
        translation_key="edge_mode",
        name="Edge mode",
        icon="mdi:border-outside",
        value_fn=lambda c: "on" if c.get_edge_mode() else "off"
        if c.get_edge_mode() is not None else None,
    ),
    RobomowSensorDescription(
        key="child_lock",
        translation_key="child_lock",
        name="Child lock",
        icon="mdi:lock-outline",
        value_fn=lambda c: "on" if c.get_child_lock() else "off"
        if c.get_child_lock() is not None else None,
    ),
    RobomowSensorDescription(
        key="anti_theft",
        translation_key="anti_theft",
        name="Anti-theft",
        icon="mdi:shield-lock-outline",
        value_fn=lambda c: "on" if c.get_anti_theft_enabled() else "off"
        if c.get_anti_theft_enabled() is not None else None,
    ),
    RobomowSensorDescription(
        key="eco_mode",
        translation_key="eco_mode",
        name="Eco mode",
        icon="mdi:leaf",
        value_fn=lambda c: "active" if c.get_eco_mode_active()
        else ("on" if c.get_eco_mode() else "off")
        if c.get_eco_mode() is not None else None,
    ),
    RobomowSensorDescription(
        key="audio",
        translation_key="audio",
        name="Audio",
        icon="mdi:volume-high",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: "on" if c.get_audio_on() else "off"
        if c.get_audio_on() is not None else None,
    ),
)

# ── Diagnostic / connection sensors ───────────────────────────────────

_DIAGNOSTIC_SENSORS: tuple[RobomowSensorDescription, ...] = (
    RobomowSensorDescription(
        key="device_last_seen",
        translation_key="device_last_seen",
        name="Last seen",
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_device_last_seen(),
    ),
    RobomowSensorDescription(
        key="firmware",
        translation_key="firmware",
        name="Firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_firmware(),
    ),
    RobomowSensorDescription(
        key="firmware_full",
        translation_key="firmware_full",
        name="Firmware (detailed)",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_firmware_full(),
    ),
    RobomowSensorDescription(
        key="hardware_version",
        translation_key="hardware_version",
        name="Hardware version",
        icon="mdi:memory",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_hardware_version(),
    ),
    RobomowSensorDescription(
        key="platform",
        translation_key="platform",
        name="Platform",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_platform(),
    ),
    RobomowSensorDescription(
        key="platform_type",
        translation_key="platform_type",
        name="Platform type",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_platform_type(),
    ),
    RobomowSensorDescription(
        key="system_failure",
        translation_key="system_failure",
        name="System failure code",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_system_failure_id(),
    ),
)

# ── All sensor descriptions combined ──────────────────────────────────

_DESCRIPTIONS: tuple[RobomowSensorDescription, ...] = (
    *_CORE_SENSORS,
    *_WIFI_SENSORS,
    *_OPERATION_SENSORS,
    *_ZONE_SENSORS,
    *_SETTINGS_SENSORS,
    *_DIAGNOSTIC_SENSORS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
    if coordinator is None:
        return
    async_add_entities(
        RobomowSensor(coordinator, desc) for desc in _DESCRIPTIONS
    )


class RobomowSensor(
    CoordinatorEntity[RobomowCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    entity_description: RobomowSensorDescription

    def __init__(
        self,
        coordinator: RobomowCoordinator,
        description: RobomowSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.serial)},
            "manufacturer": MANUFACTURER,
            "model": coordinator.get_model_name(),
            "name": (
                coordinator.device_info_raw.get("customName")
                or f"Robomow {coordinator.serial}"
            ),
            "serial_number": coordinator.serial,
        }

    @property
    def native_value(self) -> float | int | str | None:
        return self.entity_description.value_fn(self.coordinator)
