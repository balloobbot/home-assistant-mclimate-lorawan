"""PIR Mini occupancy sensor."""

from datetime import datetime
from math import floor
from typing import override

from lorawan_connection import Device, DeviceDescriptor, DeviceEvent, EventType


class PIRMini(Device):
    """PIR Mini measurements."""

    identifiers = {"tts": ("mclimate", "pir-mini")}
    model_name = "PIR Mini"

    def __init__(self, descriptor: DeviceDescriptor) -> None:
        """Initialize measurements."""
        super().__init__(descriptor)
        self.temperature: float | None = None
        self.humidity: float | None = None
        self.illuminance: int | None = None
        self.battery_voltage: float | None = None
        self.occupied: bool | None = None
        self.trigger_count: int | None = None
        self._updated: datetime | None = None

    @property
    def battery_percentage(self) -> int | None:
        """Estimate charge using the contributor's PIR Mini profile."""
        if self.battery_voltage is None:
            return None
        return floor((min(max(self.battery_voltage, 2.5), 3.0) - 2.5) / 0.5 * 100 + 0.5)

    @override
    def handle_event(self, event: DeviceEvent) -> None:
        """Decode the keepalive measurements."""
        if event.type != EventType.UPLINK or event.f_port != 2 or len(event.data) < 10:
            return
        if self._updated is not None and event.received_at < self._updated:
            return
        data = event.data[-10:]
        if data[0] != 1:
            return
        self.temperature = (((data[1] & 3) << 8 | data[2]) - 400) / 10
        self.humidity = round(data[3] * 100 / 256, 2)
        light = int.from_bytes(data[4:6], "big")
        self.illuminance = light if light <= 0xFFFA else None
        self.battery_voltage = round((data[6] * 2200 / 255 + 1600) / 1000, 2)
        self.occupied = bool(data[7] & 1)
        self.trigger_count = int.from_bytes(data[8:10], "big")
        self._updated = event.received_at
        self.notify()
