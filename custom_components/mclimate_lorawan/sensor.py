"""MClimate sensors."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MClimateConfigEntry
from ._vendor.mclimate_lorawan import MClimateDevice, PIRMini, Switch16ASPM, Vicki
from .coordinator import MClimateCoordinator
from .entity import MClimateEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class MClimateSensorDescription[DeviceT: MClimateDevice](SensorEntityDescription):
    """Select a typed measurement."""

    device_types: tuple[type[DeviceT], ...]
    value_fn: Callable[[DeviceT], float | None]


DESCRIPTIONS: tuple[MClimateSensorDescription[Any], ...] = (
    MClimateSensorDescription[Vicki | PIRMini](
        key="temperature",
        device_types=(Vicki, PIRMini),
        value_fn=lambda device: device.temperature,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MClimateSensorDescription[Vicki | PIRMini](
        key="humidity",
        device_types=(Vicki, PIRMini),
        value_fn=lambda device: device.humidity,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MClimateSensorDescription[PIRMini](
        key="illuminance",
        device_types=(PIRMini,),
        value_fn=lambda device: device.illuminance,
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MClimateSensorDescription[PIRMini](
        key="trigger_count",
        translation_key="trigger_count",
        device_types=(PIRMini,),
        value_fn=lambda device: device.trigger_count,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    MClimateSensorDescription[Vicki | PIRMini](
        key="battery",
        device_types=(Vicki, PIRMini),
        value_fn=lambda device: (
            battery
            if (battery := device.battery_level) is not None
            else device.battery_percentage
        ),
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MClimateSensorDescription[Vicki | PIRMini](
        key="battery_voltage",
        translation_key="battery_voltage",
        device_types=(Vicki, PIRMini),
        value_fn=lambda device: device.battery_voltage,
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    MClimateSensorDescription[Vicki](
        key="valve_position",
        translation_key="valve_position",
        device_types=(Vicki,),
        value_fn=lambda device: device.valve_position,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MClimateSensorDescription[Switch16ASPM](
        key="internal_temperature",
        translation_key="internal_temperature",
        device_types=(Switch16ASPM,),
        value_fn=lambda device: device.internal_temperature,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MClimateSensorDescription[Switch16ASPM](
        key="energy",
        device_types=(Switch16ASPM,),
        value_fn=lambda device: device.energy,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    MClimateSensorDescription[Switch16ASPM](
        key="power",
        device_types=(Switch16ASPM,),
        value_fn=lambda device: device.power,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MClimateSensorDescription[Switch16ASPM](
        key="voltage",
        device_types=(Switch16ASPM,),
        value_fn=lambda device: device.voltage,
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MClimateSensorDescription[Switch16ASPM](
        key="current",
        device_types=(Switch16ASPM,),
        value_fn=lambda device: device.current,
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MClimate sensors."""

    @callback
    def added(coordinator: MClimateCoordinator) -> None:
        async_add_entities(
            MClimateSensor(coordinator, description)
            for description in DESCRIPTIONS
            if isinstance(coordinator.data, description.device_types)
        )

    entry.async_on_unload(entry.runtime_data.subscribe_coordinator_added(added))


class MClimateSensor(MClimateEntity[MClimateDevice], SensorEntity):
    """Represent an MClimate measurement."""

    entity_description: MClimateSensorDescription[Any]

    @property
    @override
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.device)
