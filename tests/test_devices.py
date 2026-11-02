"""Tests for MClimate entities and commands."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import patch

from homeassistant.components.lorawan.websocket_api import _snapshot
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from lorawan_connection import (
    AckEvent,
    DeviceDescriptor,
    DownlinkError,
    StatusEvent,
    UplinkEvent,
)
from lorawan_connection.mock import MockConnection
import pytest

from custom_components.mclimate_lorawan._vendor.mclimate_lorawan import (
    PIRMini,
    Switch16ASPM,
    Vicki,
)


@pytest.fixture(
    params=[
        (Vicki, "tts"),
        (Vicki, "chirpstack"),
        (PIRMini, "tts"),
        (Switch16ASPM, "tts"),
    ]
)
def descriptor(request) -> DeviceDescriptor:
    """Select each supported catalog identity."""
    model, stack = request.param
    brand, identity = model.identifiers[stack]
    return DeviceDescriptor(
        network_id="network",
        stack=stack,
        dev_eui="0201010101010101",
        name="Garden",
        application_id="app",
        profile_id="profile",
        brand_id=brand,
        model_id=identity,
    )


@pytest.fixture
def mock_connection(descriptor) -> MockConnection:
    """Use the descriptor's backend."""
    return MockConnection([descriptor], stack_type=descriptor.stack)


@pytest.mark.usefixtures("connection_entry")
async def test_entities(hass, config_entry, mock_connection, descriptor) -> None:
    """Expose the correct entities and diagnostics for each model."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    device = config_entry.runtime_data.coordinators[
        ("network", descriptor.dev_eui)
    ].data
    if isinstance(device, Vicki):
        port, payload = 1, "011d5a78fa2c01f080"
        values = {
            "sensor.garden_temperature": "18.01",
            "sensor.garden_battery": "90",
            "climate.garden": "heat",
        }
        assert hass.states.get("climate.garden").attributes["temperature"] is None
    elif isinstance(device, PIRMini):
        port, payload = 2, "0102888002f1c80101af"
        values = {
            "sensor.garden_temperature": "24.8",
            "sensor.garden_illuminance": "753",
            "binary_sensor.garden_occupancy": "on",
            "sensor.garden_battery": "100",
        }
        assert hass.states.get("binary_sensor.garden_occupancy").state == "unknown"
        counter = er.async_get(hass).async_get("sensor.garden_pir_trigger_count")
        assert counter.entity_category is EntityCategory.DIAGNOSTIC
        assert counter.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    else:
        port, payload = 2, "011c034a241805d9e7195201"
        values = {
            "sensor.garden_energy": "55190.552",
            "sensor.garden_power": "1497",
            "sensor.garden_current": "6482",
            "switch.garden": "on",
        }
        assert hass.states.get("switch.garden").state == "unknown"
        assert er.async_get(hass).async_get("sensor.garden_battery") is None
    mock_connection.emit(
        UplinkEvent(
            descriptor=descriptor,
            received_at=datetime.now(UTC),
            f_port=port,
            data=bytes.fromhex(payload),
        )
    )
    await hass.async_block_till_done()
    for entity_id, value in values.items():
        assert hass.states.get(entity_id).state == value
    entity = er.async_get(hass).async_get(next(iter(values)))
    metadata = next(
        row
        for row in _snapshot(hass)["devices"]
        if row["dev_eui"] == descriptor.dev_eui
    )
    assert metadata["device_id"] == entity.device_id
    if not isinstance(device, Switch16ASPM):
        battery = er.async_get(hass).async_get("sensor.garden_battery")
        assert battery.entity_category is EntityCategory.DIAGNOSTIC
        assert battery.disabled_by is None
        voltage = er.async_get(hass).async_get("sensor.garden_battery_voltage")
        assert voltage.disabled_by is er.RegistryEntryDisabler.INTEGRATION
        status = StatusEvent(
            descriptor=descriptor,
            received_at=datetime.now(UTC),
            battery_level=0,
            battery_level_unavailable=False,
        )
        mock_connection.emit(status)
        await hass.async_block_till_done()
        assert hass.states.get("sensor.garden_battery").state == "0"
        mock_connection.emit(replace(status, battery_level_unavailable=True))
        await hass.async_block_till_done()
        assert (
            hass.states.get("sensor.garden_battery").state
            == values["sensor.garden_battery"]
        )
    await hass.config_entries.async_unload(config_entry.entry_id)


@pytest.mark.usefixtures("connection_entry")
@pytest.mark.parametrize("outcome", ["ack", "nack", "write_error"])
async def test_controls(
    hass, config_entry, mock_connection, descriptor, outcome
) -> None:
    """Commands wait for ACKs and preserve reported state."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    device = config_entry.runtime_data.coordinators[
        ("network", descriptor.dev_eui)
    ].data
    if isinstance(device, PIRMini):
        await hass.config_entries.async_unload(config_entry.entry_id)
        return
    if isinstance(device, Vicki):
        domain, service, data, expected = (
            "climate",
            "set_temperature",
            {"entity_id": "climate.garden", "temperature": 21.5},
            "5100d7",
        )
    else:
        domain, service, data, expected = (
            "switch",
            "turn_on",
            {"entity_id": "switch.garden"},
            "c101b1",
        )
    if outcome == "write_error":
        with patch.object(
            device, "_send_downlink", side_effect=DownlinkError("Read only")
        ):
            with pytest.raises(HomeAssistantError):
                await hass.services.async_call(domain, service, data, blocking=True)
    else:
        task = asyncio.create_task(
            hass.services.async_call(domain, service, data, blocking=True)
        )
        for _ in range(100):
            if mock_connection.downlinks:
                break
            await asyncio.sleep(0)
        queue_id, downlink = next(iter(mock_connection.downlinks.items()))
        assert downlink.data.hex() == expected
        assert downlink.f_port == 1
        assert downlink.confirmed
        assert not task.done()
        mock_connection.emit(
            AckEvent(
                descriptor=descriptor,
                received_at=datetime.now(UTC),
                queue_item_id=queue_id,
                acknowledged=outcome == "ack",
            )
        )
        if outcome == "ack":
            await task
        else:
            with pytest.raises(HomeAssistantError):
                await task
        if isinstance(device, Vicki):
            assert device.target_temperature is None
        else:
            assert device.relay_on is None
    await hass.config_entries.async_unload(config_entry.entry_id)
