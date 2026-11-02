[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=balloobbot&repository=home-assistant-mclimate-lorawan&category=integration)

# MClimate LoRaWAN

Use MClimate devices with Home Assistant's LoRaWAN connections.
Requires Home Assistant 2026.11.0b0 or newer, including 2026.11 beta releases.

## Install

1. Open the HACS link above and download the integration.
2. Restart Home Assistant.
3. Configure a LoRaWAN connection supported by your device in the table below.
4. Add your device to the network server using its catalog profile.
5. Open **Settings > Devices & services** and configure the discovered
   **MClimate LoRaWAN** integration. You can also select it under **Add integration**.

To install manually, copy `custom_components/mclimate_lorawan` into your Home
Assistant `config/custom_components` directory and restart.

## Devices

| Model | Entities | Connections |
| --- | --- | --- |
| Vicki | Thermostat, temperature, humidity, valve opening, window state, fault indicators, and battery | The Things Network / The Things Stack, ChirpStack |
| PIR Mini | Occupancy, temperature, humidity, illuminance, and battery | The Things Network / The Things Stack |
| 16A Switch & Power Meter (16ASPM) | Relay switch, power, energy, voltage, current, and internal temperature | The Things Network / The Things Stack |

In TTN, select the matching model under **MClimate**. In ChirpStack, use the
current **MClimate Vicki** catalog profile. PIR Mini and 16ASPM do not yet have
ChirpStack catalog mappings in this integration.

Devices are matched by catalog identity. Renaming a custom profile is not enough.
Readings remain unknown until the device sends an uplink or status report.

Vicki supports target temperatures from 5 to 30 °C. Fractional temperatures need
firmware that supports MClimate's precise target command (`0x51`). Heating is the
only exposed HVAC mode.

Thermostat and relay commands wait up to 30 seconds for acknowledgement. State
changes when the device reports it. Battery-powered Vicki receives downlinks
following an uplink, so a command can take longer than this. A timeout leaves the
command queued on the network server; it may still execute later.

Battery percentage uses the LoRaWAN status report when available, with a voltage
estimate as fallback. The estimates follow the contributor's profiles: 2.1–3.65 V
for Vicki and 2.5–3.0 V for PIR Mini. Battery voltage and PIR trigger count are
diagnostic entities disabled by default. Battery percentage remains enabled.
The mains-powered 16ASPM has no battery entity.

## Development

The device library is bundled under `custom_components/mclimate_lorawan/_vendor`.
Tests use TTN catalog payload examples and simulated command acknowledgements.
Physical-device testing is still needed, especially for fractional Vicki targets
and relay commands.

```sh
uv sync --group dev
uv run python script/prepare_tests.py
uv run pytest --disable-socket --allow-unix-socket
uv run ruff check .
uv run ruff format --check .
```

CI tests both the pinned Home Assistant revision and current `dev`.
When reporting a decoding issue, include the model, firmware, uplink FPort,
payload, and expected reading. Do not include API keys or device keys.

Protocols and fixtures come from [MClimate's payload helper](https://github.com/MClimate/mclimate-payload-helper)
and the [TTN device catalog](https://github.com/TheThingsNetwork/lorawan-devices/tree/master/vendor/mclimate).
Battery estimates follow [LoRaWANDeviceProfiles](https://github.com/BenAhrdt/LoRaWANDeviceProfiles/tree/main/DeviceProfiles/MClimate).
The PIR Mini uses the standard humidity conversion without the custom offset in
one of that repository's decoders.

Brand images are bundled from [MClimate's media kit](https://mclimate.eu/pages/media-kit).
