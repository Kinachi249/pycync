from __future__ import annotations

from typing import override

from pycync.exceptions import UnsupportedCapabilityError
from pycync.mappings.capabilities import DEVICE_CAPABILITIES, CyncCapability
from pycync.mappings.device_types import DEVICE_TYPES, DeviceType

_mesh_lights: list[CyncLight] = []

def create_device(device_info, mesh_device_info, home_id, device_datapoint_data = None) -> CyncDevice:
    device_type_id = mesh_device_info["deviceType"]

    device_type = DEVICE_TYPES.get(device_type_id, DeviceType.UNKNOWN)

    match device_type:
        case DeviceType.LIGHT:
            cync_light = CyncLight(device_info, mesh_device_info, home_id, device_datapoint_data)
            _mesh_lights.append(cync_light)
            return cync_light
        case _:
            return CyncDevice(device_info, mesh_device_info, home_id, device_datapoint_data)

class CyncDevice:
    def __init__(self, device_info, mesh_device_info, home_id, device_datapoint_data=None):
        if device_datapoint_data is None:
            device_datapoint_data = {}
        self.is_online = device_info["is_online"]
        self.device_id = device_info["id"]
        self.mesh_device_id = mesh_device_info["deviceID"]
        self.isolated_mesh_id = self.mesh_device_id % home_id
        self.home_id = home_id
        self.name = mesh_device_info["displayName"]
        self.device_type = mesh_device_info["deviceType"]
        self.mac = device_info["mac"]
        self.product_id = device_info["product_id"]
        self.authorize_code = device_info["authorize_code"]
        self.datapoints = device_datapoint_data

    def set_datapoints(self, datapoints):
        self.datapoints = datapoints

class CyncLight(CyncDevice):
    """Class for interacting with lights."""
    def __init__(self, device_info, mesh_device_info, home_id, device_datapoint_data):
        super().__init__(device_info, mesh_device_info, home_id, device_datapoint_data)

        self.capabilities = DEVICE_CAPABILITIES.get(self.device_type, [])
        self.self_datapoint = None

    @override
    def set_datapoints(self, datapoints):
        if self.is_online:
            self.datapoints = datapoints
            for name, datapoint_info in datapoints.items():
                if int(datapoint_info["value"][:2], 16) == self.isolated_mesh_id:
                    self.self_datapoint = datapoint_info
        else:
            global _mesh_lights
            # This device is not connected to Wi-Fi, may be Bluetooth-only. Check other mesh devices for this device's state.
            for light in [light for light in _mesh_lights if light.mesh_device_id != self.mesh_device_id]:
                mesh_datapoints = light.datapoints
                for name, datapoint_info in mesh_datapoints.items():
                    if int(datapoint_info["value"][:2], 16) == self.isolated_mesh_id:
                        self.self_datapoint = datapoint_info
                        return

    def is_on(self):
        if not self.self_datapoint:
            return False

        toggled_value = int(self.self_datapoint.get("value")[2:4], 16)
        return True if toggled_value == 1 else False

    def brightness(self):
        if CyncCapability.DIMMING not in self.capabilities:
            raise UnsupportedCapabilityError()

        if not self.self_datapoint:
            return 0

        return int(self.self_datapoint.get("value")[4:6], 16)

    def color_temp(self):
        """
        Return color temp between 1-100. Returns zero if bulb is not in color temp mode,
        or if the bulb does not have its datapoint set.
        """
        if CyncCapability.CCT_COLOR not in self.capabilities:
            raise UnsupportedCapabilityError()

        if not self.self_datapoint:
            return 0

        color_temp = int(self.self_datapoint.get("value")[6:8], 16)
        return color_temp if 1 <= color_temp <= 100 else 0

    def rgb(self):
        """
        Return RGB tuple, with each value between 1-256. Returns all zeros if bulb is not in RGB mode,
        or if the bulb does not have its datapoint set.
        """
        if CyncCapability.RGB_COLOR not in self.capabilities:
            raise UnsupportedCapabilityError()

        if not self.self_datapoint:
            return 0, 0, 0

        red = int(self.self_datapoint.get("value")[8:10], 16)
        green = int(self.self_datapoint.get("value")[10:12], 16)
        blue = int(self.self_datapoint.get("value")[12:14], 16)
        return red, green, blue