"""MClimate LoRaWAN devices."""

from lorawan_connection import DeviceCollection

from .pir_mini import PIRMini
from .relay import Switch16ASPM
from .vicki import Vicki

__all__ = ["MClimateDevice", "MClimateDevices", "PIRMini", "Switch16ASPM", "Vicki"]
type MClimateDevice = Vicki | PIRMini | Switch16ASPM


class MClimateDevices(DeviceCollection[MClimateDevice]):
    """Collect supported MClimate devices."""

    DEVICES = (Vicki, PIRMini, Switch16ASPM)
