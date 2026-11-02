"""MClimate switches."""

from asyncio import timeout
from typing import Any, override

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from lorawan_connection import DownlinkError

from . import MClimateConfigEntry
from ._vendor.mclimate_lorawan import Switch16ASPM
from .const import DOMAIN
from .coordinator import MClimateCoordinator
from .entity import MClimateEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MClimate relays."""

    @callback
    def added(coordinator: MClimateCoordinator) -> None:
        if isinstance(coordinator.data, Switch16ASPM):
            async_add_entities(
                [
                    MClimateSwitch(
                        coordinator, SwitchEntityDescription(key="relay", name=None)
                    )
                ]
            )

    entry.async_on_unload(entry.runtime_data.subscribe_coordinator_added(added))


class MClimateSwitch(MClimateEntity[Switch16ASPM], SwitchEntity):
    """Represent a 16ASPM relay."""

    @property
    @override
    def is_on(self) -> bool | None:
        return self.device.relay_on

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_relay(True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_relay(False)

    async def _async_set_relay(self, on: bool) -> None:
        try:
            async with timeout(30):
                await self.device.async_set_relay(on)
        except TimeoutError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_timeout"
            ) from err
        except DownlinkError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
