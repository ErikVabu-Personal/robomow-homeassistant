"""Binary sensor entities for the Robomow3 integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import RobomowCoordinator


@dataclass(kw_only=True, frozen=True)
class RobomowBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[RobomowCoordinator], bool | None]


_DESCRIPTIONS: tuple[RobomowBinarySensorDescription, ...] = (
    RobomowBinarySensorDescription(
        key="device_connected",
        translation_key="device_connected",
        name="Connected to cloud",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_device_connected(),
    ),
    RobomowBinarySensorDescription(
        key="device_turned_on",
        translation_key="device_turned_on",
        name="Device turned on",
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=lambda c: c.get_device_turned_on(),
    ),
    RobomowBinarySensorDescription(
        key="mow_time_complete",
        translation_key="mow_time_complete",
        name="Mow time complete",
        icon="mdi:check-circle-outline",
        value_fn=lambda c: c.get_main_zone_mow_complete(),
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
        RobomowBinarySensor(coordinator, desc) for desc in _DESCRIPTIONS
    )


class RobomowBinarySensor(
    CoordinatorEntity[RobomowCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True
    entity_description: RobomowBinarySensorDescription

    def __init__(
        self,
        coordinator: RobomowCoordinator,
        description: RobomowBinarySensorDescription,
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
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator)
