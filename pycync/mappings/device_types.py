from enum import Enum

class DeviceType(Enum):
    LIGHT = "light"
    SWITCH = "switch"
    THERMOSTAT = "thermostat"
    UNKNOWN = "unknown"

DEVICE_TYPES = {
    131: DeviceType.LIGHT, # DirectConnectFullColorBulbA19
    137: DeviceType.LIGHT, # SingleChipFullColorBulbA19
}