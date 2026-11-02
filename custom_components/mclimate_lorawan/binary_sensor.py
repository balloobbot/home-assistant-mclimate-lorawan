"""MClimate binary sensors."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MClimateConfigEntry
from ._vendor.mclimate_lorawan import MClimateDevice, PIRMini, Vicki
from .coordinator import MClimateCoordinator
from .entity import MClimateEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class MClimateBinaryDescription[DeviceT: MClimateDevice](BinarySensorEntityDescription):
    """Select a typed device state."""

    device_types: tuple[type[DeviceT], ...]
    value_fn: Callable[[DeviceT], bool | None]


DESCRIPTIONS: tuple[MClimateBinaryDescription[Any], ...] = (
    MClimateBinaryDescription[PIRMini](
        key="occupancy",
        device_types=(PIRMini,),
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda device: device.occupied,
    ),
    MClimateBinaryDescription[Vicki](
        key="window",
        device_types=(Vicki,),
        device_class=BinarySensorDeviceClass.WINDOW,
        value_fn=lambda device: device.window_open,
    ),
    MClimateBinaryDescription[Vicki](
        key="motor_problem",
        translation_key="motor_problem",
        device_types=(Vicki,),
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.motor_problem,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MClimateBinaryDescription[Vicki](
        key="sensor_problem",
        translation_key="sensor_problem",
        device_types=(Vicki,),
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.sensor_problem,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MClimateBinaryDescription[Vicki](
        key="calibration_failed",
        translation_key="calibration_failed",
        device_types=(Vicki,),
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.calibration_failed,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MClimate binary sensors."""

    @callback
    def added(coordinator: MClimateCoordinator) -> None:
        async_add_entities(
            MClimateBinarySensor(coordinator, description)
            for description in DESCRIPTIONS
            if isinstance(coordinator.data, description.device_types)
        )

    entry.async_on_unload(entry.runtime_data.subscribe_coordinator_added(added))


class MClimateBinarySensor(MClimateEntity[MClimateDevice], BinarySensorEntity):
    """Represent an MClimate binary state."""

    entity_description: MClimateBinaryDescription[Any]

    @property
    @override
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.device)
