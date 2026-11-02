"""MClimate entities."""

from typing import override

from homeassistant.components.lorawan import LoRaWANEntity
from homeassistant.helpers.device_registry import DeviceInfo

from ._vendor.mclimate_lorawan import MClimateDevice
from .coordinator import MClimateCoordinator


class MClimateEntity[DeviceT: MClimateDevice](LoRaWANEntity[DeviceT]):
    """Share device information between MClimate entities."""

    coordinator: MClimateCoordinator

    @property
    @override
    def device_info(self) -> DeviceInfo:
        return self.coordinator.device_info
