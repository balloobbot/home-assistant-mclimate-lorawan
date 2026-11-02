"""Tests for MClimate payloads."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from lorawan_connection import UplinkEvent
import pytest

from custom_components.mclimate_lorawan._vendor.mclimate_lorawan import (
    PIRMini,
    Switch16ASPM,
    Vicki,
)


@pytest.mark.parametrize(
    ("model", "port", "payload", "expected"),
    [
        (
            Vicki,
            1,
            "011d5a78fa2c01f080",
            {
                "temperature": 18.01,
                "humidity": 46.88,
                "target_temperature": 29,
                "valve_position": 17,
                "battery_voltage": 3.5,
                "battery_percentage": 90,
                "child_lock": True,
                "window_open": False,
            },
        ),
        (
            PIRMini,
            2,
            "0102888002f1c80101af",
            {
                "temperature": 24.8,
                "humidity": 50,
                "illuminance": 753,
                "battery_voltage": 3.33,
                "battery_percentage": 100,
                "occupied": True,
                "trigger_count": 431,
            },
        ),
        (
            PIRMini,
            2,
            "120a0102809903e1cc010012",
            {
                "temperature": 24,
                "humidity": 59.77,
                "illuminance": 993,
                "battery_voltage": 3.36,
                "occupied": True,
                "trigger_count": 18,
            },
        ),
        (
            PIRMini,
            2,
            "3a0102809903e1cc010012",
            {
                "temperature": 24,
                "humidity": 59.77,
                "occupied": True,
                "trigger_count": 18,
            },
        ),
        (
            Switch16ASPM,
            2,
            "011c034a241805d9e7195201",
            {
                "internal_temperature": 28,
                "energy": 55190.552,
                "power": 1497,
                "voltage": 231,
                "current": 6482,
                "relay_on": True,
            },
        ),
    ],
)
def test_catalog_payloads(descriptor, model, port, payload, expected) -> None:
    """Reproduce the TTN catalog decoder examples."""
    device = model(descriptor)
    event = UplinkEvent(
        descriptor=descriptor,
        received_at=datetime.now(UTC),
        f_port=port,
        data=bytes.fromhex(payload),
    )
    device.handle_event(event)
    for key, value in expected.items():
        assert getattr(device, key) == value
    for invalid in [
        replace(event, data=b""),
        replace(
            event,
            data=event.data[
                -(9 if model is Vicki else 10 if model is PIRMini else 12) :
            ][:-1],
        ),
        replace(event, f_port=99),
    ]:
        device.handle_event(invalid)
        for key, value in expected.items():
            assert getattr(device, key) == value


@pytest.mark.parametrize(
    ("model", "payload", "port", "key", "expected"),
    [
        (Vicki, "81016400fa2c01f080", 1, "temperature", 12.65),
        (Vicki, "5200d7011d5a78fa2c01f080", 1, "target_temperature", 21.5),
        (PIRMini, "01000000ffff8b000000", 2, "temperature", -40),
        (Switch16ASPM, "011cffffffff0000e7000000", 2, "energy", 4294967.295),
    ],
)
def test_numeric_cases(descriptor, model, payload, port, key, expected) -> None:
    """Handle negative temperatures, precise targets, and unsigned counters."""
    device = model(descriptor)
    device.handle_event(
        UplinkEvent(
            descriptor=descriptor,
            received_at=datetime.now(UTC),
            f_port=port,
            data=bytes.fromhex(payload),
        )
    )
    assert getattr(device, key) == expected


@pytest.mark.parametrize("light", [0xFFFB, 0xFFFC, 0xFFFD, 0xFFFE, 0xFFFF])
def test_disabled_light(descriptor, light) -> None:
    """Unavailable light readings stay unknown."""
    device = PIRMini(descriptor)
    data = (
        bytes.fromhex("01028880") + light.to_bytes(2, "big") + bytes.fromhex("c80101af")
    )
    device.handle_event(
        UplinkEvent(
            descriptor=descriptor, received_at=datetime.now(UTC), f_port=2, data=data
        )
    )
    assert device.illuminance is None
    assert device.occupied is True


def test_older_report(descriptor) -> None:
    """An older report does not replace current state."""
    device = PIRMini(descriptor)
    event = UplinkEvent(
        descriptor=descriptor,
        received_at=datetime.now(UTC),
        f_port=2,
        data=bytes.fromhex("0102888002f1c80101af"),
    )
    device.handle_event(event)
    device.handle_event(
        replace(
            event,
            received_at=event.received_at - timedelta(seconds=1),
            data=bytes.fromhex("01000000000000000000"),
        )
    )
    assert device.temperature == 24.8


@pytest.mark.parametrize("temperature", [float("nan"), float("inf"), 4, 31])
async def test_invalid_target(descriptor, temperature) -> None:
    """Reject invalid temperatures before sending."""
    with pytest.raises(ValueError):
        await Vicki(descriptor).async_set_temperature(temperature)


@pytest.mark.parametrize(
    ("model", "method", "value", "payload"),
    [
        (Vicki, "async_set_temperature", 21, "0e15"),
        (Vicki, "async_set_temperature", 21.5, "5100d7"),
        (Switch16ASPM, "async_set_relay", True, "c101b1"),
        (Switch16ASPM, "async_set_relay", False, "c100b1"),
    ],
)
async def test_commands(descriptor, model, method, value, payload) -> None:
    """Encode the manufacturer's temperature and relay commands."""
    device = model(descriptor)
    with patch.object(device, "async_send_downlink") as send:
        await getattr(device, method)(value)
    send.assert_awaited_once_with(data=bytes.fromhex(payload), f_port=1)
