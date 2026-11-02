"""MClimate thermostats."""

from asyncio import timeout
from typing import Any, override

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from lorawan_connection import DownlinkError

from . import MClimateConfigEntry
from ._vendor.mclimate_lorawan import Vicki
from .const import DOMAIN
from .coordinator import MClimateCoordinator
from .entity import MClimateEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Vicki thermostats."""

    @callback
    def added(coordinator: MClimateCoordinator) -> None:
        if isinstance(coordinator.data, Vicki):
            async_add_entities(
                [
                    VickiClimate(
                        coordinator,
                        ClimateEntityDescription(key="thermostat", name=None),
                    )
                ]
            )

    entry.async_on_unload(entry.runtime_data.subscribe_coordinator_added(added))


class VickiClimate(MClimateEntity[Vicki], ClimateEntity):
    """Represent a Vicki thermostat."""

    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 5
    _attr_max_temp = 30
    _attr_target_temperature_step = 0.1
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT

    @property
    @override
    def current_temperature(self) -> float | None:
        return self.device.temperature

    @property
    @override
    def current_humidity(self) -> float | None:
        return self.device.humidity

    @property
    @override
    def target_temperature(self) -> float | None:
        return self.device.target_temperature

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        try:
            async with timeout(30):
                await self.device.async_set_temperature(kwargs[ATTR_TEMPERATURE])
        except TimeoutError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_timeout"
            ) from err
        except (DownlinkError, ValueError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
