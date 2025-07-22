from __future__ import annotations

from abc import ABC, abstractmethod
from .devices import CyncDevice
from pycync.mappings.capabilities import CyncCapability

class GroupedCyncDevices(ABC):
    @abstractmethod
    def get_common_capabilities(self) -> frozenset[CyncCapability]:
        pass

    @abstractmethod
    def get_device_types(self) -> frozenset[type[CyncDevice]]:
        pass

class CyncHome(GroupedCyncDevices):
    def __init__(self, name: str, home_id: int, rooms: list[CyncRoom], global_devices: list[CyncDevice]):
        self.name = name
        self.home_id = home_id
        self.rooms = rooms
        self.global_devices = global_devices

    def contains_device_id(self, device_id: int):
        search_result = next((device for device in self.get_flattened_device_list() if device.device_id == device_id), None)

        return search_result is not None

    def get_flattened_device_list(self) -> list[CyncDevice]:
        home_devices = self.global_devices.copy()

        for room in self.rooms:
            home_devices.extend(room.devices)
            for group in room.groups:
                home_devices.extend(group.devices)

        return home_devices

    def get_common_capabilities(self) -> frozenset[CyncCapability]:
        all_capabilities = frozenset({capability for capability in CyncCapability})
        return (all_capabilities
                .intersection([frozenset(device.capabilities) for device in self.global_devices])
                .intersection([group.get_common_capabilities() for group in self.rooms]))

    def get_device_types(self) -> frozenset[type[CyncDevice]]:
        return frozenset({type(device) for device in self.global_devices}).union([room.get_device_types() for room in self.rooms])


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

    def get_device_types(self) -> frozenset[type[CyncDevice]]:
        return frozenset({type(device) for device in self.devices}).union([group.get_device_types() for group in self.groups])

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

    def get_device_types(self) -> frozenset[type[CyncDevice]]:
        return frozenset({type(device) for device in self.devices})

    def set_update_callback(self, callback):
        self.on_update = callback