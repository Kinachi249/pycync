from __future__ import annotations

from abc import ABC, abstractmethod
from pycync import CyncDevice
from pycync.mappings.capabilities import CyncCapability


class CyncHome:
    def __init__(self, name: str, home_id: int, rooms: list[CyncRoom], global_devices: list[CyncDevice]):
        self.name = name
        self.home_id = home_id
        self.rooms = rooms
        self.global_devices = global_devices


class GroupedCyncDevices(ABC):
    @abstractmethod
    def get_common_capabilities(self) -> frozenset[CyncCapability]:
        pass

    @abstractmethod
    def get_group_device_types(self) -> frozenset[type[CyncDevice]]:
        pass


class CyncRoom(GroupedCyncDevices):
    def __init__(self, name: str, room_id: int, groups: list[CyncGroup], devices: list[CyncDevice]):
        self.name = name
        self.room_id = room_id
        self.groups = groups
        self.devices = devices
        self.on_update = None

    def get_common_capabilities(self) -> frozenset[CyncCapability]:
        all_capabilities = frozenset({capability for capability in CyncCapability})
        return (all_capabilities
                .intersection([frozenset(device.capabilities) for device in self.devices])
                .intersection([group.get_common_capabilities() for group in self.groups]))

    def get_group_device_types(self) -> frozenset[type[CyncDevice]]:
        return frozenset({type(device) for device in self.devices}).union([group.get_group_device_types() for group in self.groups])

    def set_update_callback(self, callback):
        self.on_update = callback


class CyncGroup(GroupedCyncDevices):
    def __init__(self, name: str, group_id: int, devices: list[CyncDevice]):
        self.name = name
        self.group_id = group_id
        self.devices = devices
        self.on_update = None

    def get_common_capabilities(self) -> frozenset[CyncCapability]:
        all_capabilities = frozenset({capability for capability in CyncCapability})
        return all_capabilities.intersection([frozenset(device.capabilities) for device in self.devices])

    def get_group_device_types(self) -> frozenset[type[CyncDevice]]:
        return frozenset({type(device) for device in self.devices})

    def set_update_callback(self, callback):
        self.on_update = callback