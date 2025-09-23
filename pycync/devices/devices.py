"""Contains definitions for various Cync devices."""

from __future__ import annotations

from typing import Tuple, Any

from .controllable import CyncControllable
from pycync.exceptions import UnsupportedCapabilityError
from pycync.tcp.command_client import CommandClient
from pycync.devices.capabilities import DEVICE_CAPABILITIES, CyncCapability
from pycync.devices.device_types import DEVICE_TYPES, DeviceType


def create_device(device_info: dict[str, Any], mesh_device_info: dict[str, Any], home_id: int,
                  command_client: CommandClient, wifi_connected: bool = False,
                  device_datapoint_data: dict[str, Any] = None) -> CyncDevice:
    device_type_id = mesh_device_info["deviceType"]

    is_online = device_info.get("is_online", False)
    wifi_connected = wifi_connected
    device_id = device_info.get("id")
    mesh_device_id = mesh_device_info.get("deviceID")
    name = mesh_device_info.get("displayName")
    device_type = DEVICE_TYPES.get(device_type_id, DeviceType.UNKNOWN)
    mac = device_info.get("mac")
    product_id = device_info.get("product_id")
    authorize_code = device_info.get("authorize_code")

    match device_type:
        case (DeviceType.LIGHT |
              DeviceType.INDOOR_LIGHT_STRIP |
              DeviceType.OUTDOOR_LIGHT_STRIP |
              DeviceType.NEON_LIGHT_STRIP |
              DeviceType.OUTDOOR_NEON_LIGHT_STRIP |
              DeviceType.CAFE_STRING_LIGHTS |
              DeviceType.DOWNLIGHT |
              DeviceType.UNDERCABINET_FIXTURES |
              DeviceType.LIGHT_TILE):
            return CyncLight(
                is_online,
                wifi_connected,
                device_id,
                mesh_device_id,
                home_id,
                name,
                device_type_id,
                device_type,
                mac,
                product_id,
                authorize_code,
                datapoints=device_datapoint_data,
                command_client=command_client)
        case _:
            return CyncDevice(
                is_online,
                wifi_connected,
                device_id,
                mesh_device_id,
                home_id,
                name,
                device_type_id,
                device_type,
                mac,
                product_id,
                authorize_code,
                device_datapoint_data,
                command_client
            )


class CyncDevice(CyncControllable):
    """Definition for a generic Cync device, with the common attributes shared between device types."""

    def __init__(self,
                 is_online: bool,
                 wifi_connected: bool,
                 device_id: int,
                 mesh_device_id: int,
                 home_id: int,
                 name: str,
                 device_type_id: int,
                 device_type: DeviceType,
                 mac_address: str,
                 product_id: str,
                 authorize_code: str,
                 datapoints: dict[str, Any] = None,
                 command_client: CommandClient = None,
                 ):
        if datapoints is None:
            datapoints = {}

        self.is_online = is_online
        self.wifi_connected = wifi_connected
        self.device_id = device_id
        self.mesh_device_id = mesh_device_id
        self.parent_home_id = home_id
        self.isolated_mesh_id = self.mesh_device_id % self.parent_home_id
        self._name = name
        self.device_type = device_type
        self.mac = mac_address
        self.product_id = product_id
        self.authorize_code = authorize_code
        self.datapoints = datapoints
        self.device_type_id = device_type_id
        self._capabilities = DEVICE_CAPABILITIES.get(self.device_type_id, {})
        self._command_client = command_client

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CyncDevice:
        is_online = data.get("is_online")
        wifi_connected = data.get("wifi_connected")
        device_id = data.get("device_id")
        mesh_device_id = data.get("mesh_device_id")
        home_id = data.get("home_id")
        name = data.get("name")
        device_type_id = data.get("device_type_id")
        device_type = DeviceType[data.get("device_type")]
        mac_address = data.get("mac_address")
        product_id = data.get("product_id")
        authorize_code = data.get("authorize_code")

        match device_type:
            case (DeviceType.LIGHT |
                  DeviceType.INDOOR_LIGHT_STRIP |
                  DeviceType.OUTDOOR_LIGHT_STRIP |
                  DeviceType.NEON_LIGHT_STRIP |
                  DeviceType.OUTDOOR_NEON_LIGHT_STRIP |
                  DeviceType.CAFE_STRING_LIGHTS |
                  DeviceType.DOWNLIGHT |
                  DeviceType.UNDERCABINET_FIXTURES |
                  DeviceType.LIGHT_TILE):
                return CyncLight(
                    is_online,
                    wifi_connected,
                    device_id,
                    mesh_device_id,
                    home_id,
                    name,
                    device_type_id,
                    device_type,
                    mac_address,
                    product_id,
                    authorize_code,
                    data.get("is_on", False),
                    data.get("brightness", 0),
                    data.get("color_temp", 0),
                    data.get("rgb", (0, 0, 0)))
            case _:
                return CyncDevice(
                    is_online,
                    wifi_connected,
                    device_id,
                    mesh_device_id,
                    home_id,
                    name,
                    device_type_id,
                    device_type,
                    mac_address,
                    product_id,
                    authorize_code
                )

    def set_wifi_connected(self, wifi_connected: bool):
        self.wifi_connected = wifi_connected

    def set_datapoints(self, datapoints: dict[str, Any]):
        """Currently not used. Will be once datapoint-driven devices are implemented."""
        self.datapoints = datapoints

    @property
    def capabilities(self) -> frozenset[CyncCapability]:
        return self._capabilities

    @property
    def name(self) -> str:
        return self._name

    @property
    def mesh_reference_id(self) -> int:
        return self.isolated_mesh_id

    @property
    def unique_id(self) -> str:
        return f"{self.parent_home_id}-{self.device_id}"

    def supports_capability(self, capability: CyncCapability) -> bool:
        return capability in self.capabilities


class CyncLight(CyncDevice):
    """Class for representing Cync lights."""

    def __init__(self,
                 is_online: bool,
                 wifi_connected: bool,
                 device_id: int,
                 mesh_device_id: int,
                 home_id: int,
                 name: str,
                 device_type_id: int,
                 device_type: DeviceType,
                 mac_address: str,
                 product_id: str,
                 authorize_code: str,
                 is_on: bool = False,
                 brightness: int = 0,
                 color_temp: int = 0,
                 rgb: (int, int, int) = (0, 0, 0),
                 datapoints: dict[str, Any] = None,
                 command_client: CommandClient = None, ):
        super().__init__(is_online,
                         wifi_connected,
                         device_id,
                         mesh_device_id,
                         home_id,
                         name,
                         device_type_id,
                         device_type,
                         mac_address,
                         product_id,
                         authorize_code,
                         datapoints,
                         command_client)

        self._is_on = is_on
        self._brightness = brightness
        self._color_temp = color_temp
        self._rgb = rgb

    @property
    def is_on(self) -> bool:
        if not self.supports_capability(CyncCapability.ON_OFF):
            raise UnsupportedCapabilityError()

        return self._is_on

    @property
    def brightness(self) -> int:
        if not self.supports_capability(CyncCapability.DIMMING):
            raise UnsupportedCapabilityError()

        return self._brightness

    @property
    def color_temp(self) -> int:
        """
        Return color temp between 1-100. Returns zero if bulb is not in color temp mode,
        or if the bulb does not have its datapoint set.
        """
        if not self.supports_capability(CyncCapability.CCT_COLOR):
            raise UnsupportedCapabilityError()

        return self._color_temp if 1 <= self._color_temp <= 100 else 0

    @property
    def color_mode(self) -> int:
        """
        A more generalized version of 'color temp', as this field is also used to store state that indicates
        when the light is in RGB mode and effect modes.
        """
        return self._color_temp

    @property
    def rgb(self) -> Tuple[int, int, int]:
        """
        Return RGB tuple, with each value between 1-256. Returns all zeros if bulb is not in RGB mode,
        or if the bulb does not have its datapoint set.
        """
        if not self.supports_capability(CyncCapability.RGB_COLOR):
            raise UnsupportedCapabilityError()

        return self._rgb

    def update_state(self, is_on: bool, brightness: int = None, color_temp: int = None,
                     rgb: Tuple[int, int, int] = None, is_online: bool = None):
        self._is_on = is_on
        if brightness is not None:
            self._brightness = brightness
        if color_temp is not None:
            self._color_temp = color_temp
        if rgb is not None:
            self._rgb = rgb
        if is_online is not None:
            self.is_online = is_online

    async def turn_on(self):
        if not self.supports_capability(CyncCapability.ON_OFF):
            raise UnsupportedCapabilityError()

        await self._command_client.set_power_state(self, True)

    async def turn_off(self):
        if not self.supports_capability(CyncCapability.ON_OFF):
            raise UnsupportedCapabilityError()

        await self._command_client.set_power_state(self, False)

    async def set_brightness(self, brightness):
        if not self.supports_capability(CyncCapability.DIMMING):
            raise UnsupportedCapabilityError()

        await self._command_client.set_brightness(self, brightness)

    async def set_color_temp(self, color_temp):
        if not self.supports_capability(CyncCapability.CCT_COLOR):
            raise UnsupportedCapabilityError()

        await self._command_client.set_color_temp(self, color_temp)

    async def set_rgb(self, rgb: tuple[int, int, int]):
        if not self.supports_capability(CyncCapability.RGB_COLOR):
            raise UnsupportedCapabilityError()

        await self._command_client.set_rgb(self, rgb)
