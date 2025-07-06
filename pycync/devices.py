from __future__ import annotations

from pycync.exceptions import UnsupportedCapabilityError
from pycync.mappings.capabilities import DEVICE_CAPABILITIES, CyncCapability
from pycync.mappings.device_types import DEVICE_TYPES, DeviceType

_mesh_lights: list[CyncLight] = []

def create_device(device_info, mesh_device_info, home_id, device_datapoint_data = None) -> CyncDevice:
    device_type_id = mesh_device_info["deviceType"]

    device_type = DEVICE_TYPES.get(device_type_id, DeviceType.UNKNOWN)

    match device_type:
        case DeviceType.LIGHT | DeviceType.INDOOR_LIGHT_STRIP | DeviceType.OUTDOOR_LIGHT_STRIP:
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
        self.on_update = None
        self.datapoints = device_datapoint_data

    def set_datapoints(self, datapoints):
        self.datapoints = datapoints

    def set_update_callback(self, callback):
        self.on_update = callback

class CyncLight(CyncDevice):
    """Class for interacting with lights."""
    def __init__(self, device_info, mesh_device_info, home_id, device_datapoint_data):
        super().__init__(device_info, mesh_device_info, home_id, device_datapoint_data)

        self.capabilities = DEVICE_CAPABILITIES.get(self.device_type, [])
        self.is_on = False
        self.brightness = 0
        self.color_temp = 0
        self.rgb = 0, 0, 0

    def is_on(self):
        return self.is_on

    def brightness(self):
        if CyncCapability.DIMMING not in self.capabilities:
            raise UnsupportedCapabilityError()

        return self.brightness

    def color_temp(self):
        """
        Return color temp between 1-100. Returns zero if bulb is not in color temp mode,
        or if the bulb does not have its datapoint set.
        """
        if CyncCapability.CCT_COLOR not in self.capabilities:
            raise UnsupportedCapabilityError()

        return self.color_temp if 1 <= self.color_temp <= 100 else 0

    def rgb(self):
        """
        Return RGB tuple, with each value between 1-256. Returns all zeros if bulb is not in RGB mode,
        or if the bulb does not have its datapoint set.
        """
        if CyncCapability.RGB_COLOR not in self.capabilities:
            raise UnsupportedCapabilityError()

        return self.rgb