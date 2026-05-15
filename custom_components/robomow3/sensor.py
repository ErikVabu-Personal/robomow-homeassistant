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


_DESCRIPTIONS: tuple[RobomowSensorDescription, ...] = (
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
    RobomowSensorDescription(
        key="next_operation",
        translation_key="next_operation",
        name="Next mowing",
        icon="mdi:calendar-clock",
        value_fn=lambda c: c.get_next_operation().get("startOperationDate"),
    ),
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
