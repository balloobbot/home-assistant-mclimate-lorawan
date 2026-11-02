"""Vicki radiator thermostat."""

from datetime import datetime
from math import floor, isfinite
from typing import override

from lorawan_connection import Device, DeviceDescriptor, DeviceEvent, EventType


class Vicki(Device):
    """Vicki measurements and temperature control."""

    identifiers = {
        "tts": ("mclimate", "vicki"),
        "chirpstack": (824, "c521e66f-5745-45a0-b483-00fe1db8eaac"),
    }
    model_name = "Vicki"

    def __init__(self, descriptor: DeviceDescriptor) -> None:
        """Initialize measurements."""
        super().__init__(descriptor)
        self.temperature: float | None = None
        self.humidity: float | None = None
        self.target_temperature: float | None = None
        self.battery_voltage: float | None = None
        self.valve_position: int | None = None
        self.window_open: bool | None = None
        self.child_lock: bool | None = None
        self.motor_problem: bool | None = None
        self.sensor_problem: bool | None = None
        self.calibration_failed: bool | None = None
        self._updated: datetime | None = None

    @property
    def battery_percentage(self) -> int | None:
        """Estimate charge using the contributor's Vicki profile."""
        if self.battery_voltage is None:
            return None
        return floor(
            (min(max(self.battery_voltage, 2.1), 3.65) - 2.1) / (3.65 - 2.1) * 100 + 0.5
        )

    @override
    def handle_event(self, event: DeviceEvent) -> None:
        """Decode a keepalive, including one appended to a command response."""
        if event.type != EventType.UPLINK or event.f_port != 1 or len(event.data) < 9:
            return
        if self._updated is not None and event.received_at < self._updated:
            return
        data = event.data[-9:]
        if data[0] not in (1, 0x81):
            return
        temperature = (
            data[2] * 165 / 256 - 40 if data[0] == 1 else (data[2] - 28.33333) / 5.66666
        )
        motor_range = ((data[6] & 15) << 8) | data[5]
        motor_position = ((data[6] >> 4) << 8) | data[4]
        self.temperature = round(temperature, 2)
        self.humidity = round(data[3] * 100 / 256, 2)
        self.target_temperature = float(data[1])
        self.battery_voltage = round(2 + (data[7] >> 4) * 0.1, 2)
        self.valve_position = (
            floor((1 - motor_position / motor_range) * 100 + 0.5) if motor_range else 0
        )
        self.window_open = bool(data[7] & 8)
        self.motor_problem = bool(data[7] & 6)
        self.sensor_problem = bool(data[7] & 1)
        self.child_lock = bool(data[8] & 0x80)
        self.calibration_failed = bool(data[8] & 0x40)
        # A precise target response consists of 0x52 and two bytes before the keepalive.
        if len(event.data) == 12 and event.data[0] == 0x52:
            self.target_temperature = int.from_bytes(event.data[1:3], "big") / 10
        self._updated = event.received_at
        self.notify()

    async def async_set_temperature(self, temperature: float) -> None:
        """Set a target from 5 to 30 degrees Celsius."""
        if not isfinite(temperature) or not 5 <= temperature <= 30:
            raise ValueError("Temperature must be between 5 and 30 degrees Celsius")
        if float(temperature).is_integer():
            payload = bytes((0x0E, int(temperature)))
        else:
            payload = bytes((0x51,)) + floor(temperature * 10 + 0.5).to_bytes(2, "big")
        await self.async_send_downlink(data=payload, f_port=1)
