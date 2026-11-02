"""16A Switch and Power Meter."""

from datetime import datetime
from typing import override

from lorawan_connection import Device, DeviceDescriptor, DeviceEvent, EventType


class Switch16ASPM(Device):
    """16ASPM metering and relay control."""

    identifiers = {"tts": ("mclimate", "16aspm")}
    model_name = "16ASPM"

    def __init__(self, descriptor: DeviceDescriptor) -> None:
        """Initialize measurements."""
        super().__init__(descriptor)
        self.internal_temperature: int | None = None
        self.energy: float | None = None
        self.power: int | None = None
        self.voltage: int | None = None
        self.current: int | None = None
        self.relay_on: bool | None = None
        self._updated: datetime | None = None

    @override
    def handle_event(self, event: DeviceEvent) -> None:
        """Decode a metering report."""
        if event.type != EventType.UPLINK or event.f_port != 2 or len(event.data) < 12:
            return
        if self._updated is not None and event.received_at < self._updated:
            return
        data = event.data[-12:]
        if data[0] != 1 or data[11] not in (0, 1):
            return
        self.internal_temperature = data[1]
        self.energy = int.from_bytes(data[2:6], "big") / 1000
        self.power = int.from_bytes(data[6:8], "big")
        self.voltage = data[8]
        self.current = int.from_bytes(data[9:11], "big")
        self.relay_on = bool(data[11])
        self._updated = event.received_at
        self.notify()

    async def async_set_relay(self, on: bool) -> None:
        """Set the relay and request its reported state."""
        await self.async_send_downlink(data=bytes((0xC1, int(on), 0xB1)), f_port=1)
