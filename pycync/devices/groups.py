"""Definitions for groupings used in the Cync API."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .controllable import CyncControllable
from pycync.devices import CyncDevice
from pycync.exceptions import UnsupportedCapabilityError
from pycync.tcp.command_client import CommandClient
from pycync.devices.capabilities import CyncCapability


class GroupedCyncDevices(ABC):
    """Abstract definition for a Cync device grouping."""

    @abstractmethod
    def get_device_types(self) -> frozenset[type[CyncDevice]]:
        """Returns all distinct device types found in the group."""
        pass


class CyncHome:
    """Represents a "home" in the Cync app."""

    def __init__(self, name: str, home_id: int, rooms: list[CyncRoom], global_devices: list[CyncDevice]):
        self.name = name
        self.home_id = home_id
        self.rooms = rooms
        self.global_devices = global_devices

    def contains_device_id(self, device_id: int) -> bool:
        """
        Determines whether a given device ID exists in this home.
        The home is searched recursively, so each room and group within the home will be searched.
        """

        search_result = next((device for device in self.get_flattened_device_list() if device.device_id == device_id),
                             None)

        return search_result is not None

    def get_flattened_device_list(self) -> list[CyncDevice]:
        """
        Returns a flattened list of all devices in the home, across all rooms and groups.
        """

        home_devices = self.global_devices.copy()

        for room in self.rooms:
            home_devices.extend(room.devices)
            for group in room.groups:
                home_devices.extend(group.devices)

        return home_devices


class CyncRoom(GroupedCyncDevices, CyncControllable):
    """Represents a "room" in the Cync app."""

    def __init__(self, name: str, room_id: int, parent_home: CyncHome, groups: list[CyncGroup],
                 devices: list[CyncDevice], command_client: CommandClient):
        self._name = name
        self.room_id = room_id
        self.parent_home = parent_home
        self.groups = groups
        self.devices = devices
        self._command_client = command_client

    @property
    def capabilities(self) -> frozenset[CyncCapability]:
        all_capabilities = frozenset({capability for capability in CyncCapability})
        return (all_capabilities
                .intersection([frozenset(device.capabilities) for device in self.devices])
                .intersection([group.capabilities for group in self.groups]))

    @property
    def name(self) -> str:
        return self._name

    @property
    def mesh_reference_id(self) -> int:
        return self.room_id

    @property
    def unique_id(self) -> str:
        return f"{self.parent_home.home_id}-{self.room_id}"

    def supports_capability(self, capability: CyncCapability) -> bool:
        return capability in self.capabilities

    def get_device_types(self) -> frozenset[type[CyncDevice]]:
        return frozenset({type(device) for device in self.devices}).union(
            [group.get_device_types() for group in self.groups])

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


class CyncGroup(GroupedCyncDevices, CyncControllable):
    """Represents a "group" in the Cync app."""

    def __init__(self, name: str, group_id: int, parent_home: CyncHome, devices: list[CyncDevice],
                 command_client: CommandClient):
        self._name = name
        self.group_id = group_id
        self.parent_home = parent_home
        self.devices = devices
        self._command_client = command_client

    @property
    def capabilities(self) -> frozenset[CyncCapability]:
        all_capabilities = frozenset({capability for capability in CyncCapability})
        return all_capabilities.intersection([frozenset(device.capabilities) for device in self.devices])

    @property
    def name(self) -> str:
        return self._name

    @property
    def mesh_reference_id(self) -> int:
        return self.group_id

    @property
    def unique_id(self) -> str:
        return f"{self.parent_home.home_id}-{self.group_id}"

    def supports_capability(self, capability: CyncCapability) -> bool:
        return capability in self.capabilities

    def get_device_types(self) -> frozenset[type[CyncDevice]]:
        return frozenset({type(device) for device in self.devices})

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
