import asyncio
from typing import Callable

from pycync import Auth
from pycync.core.devices import create_device, CyncDevice
from pycync.exceptions import MissingAuthError
from pycync.const import REST_API_BASE_URL
from pycync.core.groups import CyncRoom, CyncGroup, CyncHome
from pycync.management.command_client import CommandClient
from pycync.management import device_storage


class Cync:
    """Docs."""
    def __init__(self, auth: Auth):
        """Initialize the Cync object."""
        if not auth.user:
            raise MissingAuthError("No logged in user exists on auth object.")
        self._auth = auth
        self._command_client = None

    @classmethod
    async def create(cls, auth: Auth):
        cync_api = Cync(auth)

        await cync_api.refresh_home_info()
        cync_api._start_command_client()

        return cync_api

    def get_logged_in_user(self):
        """Get logged in user."""

        return self._auth.user

    def set_update_callback(self, update_callback: Callable):
        device_storage.set_user_device_callback(self._auth.user.user_id, update_callback)

    def update_device_states(self):
        """Update device states."""
        asyncio.create_task(self._command_client.update_mesh_devices())

    def get_devices(self):
        """Get list of devices."""
        return device_storage.get_flattened_devices(self._auth.user.user_id)

    def get_homes(self):
        """Get all homes, devices, and groups for the account."""
        return device_storage.get_user_homes(self._auth.user.user_id)

    async def refresh_home_info(self):
        """Refresh home info."""
        device_info = await self._auth.send_user_request(
            f"{REST_API_BASE_URL}/v2/user/{self._auth.user.user_id}/subscribe/devices")
        home_entries = [device for device in device_info if device["source"] == 5]
        homes = []

        for home in home_entries:
            home_devices: list[CyncDevice] = []
            rooms: list[CyncRoom] = []
            groups: list[CyncGroup] = []

            mesh_device_info = await self._auth.send_user_request(
                f"{REST_API_BASE_URL}/v2/product/{home["product_id"]}/device/{home["id"]}/property")
            if "bulbsArray" in mesh_device_info:
                mesh_devices = mesh_device_info["bulbsArray"]
                for mesh_device in mesh_devices:
                    matching_device = next(device for device in device_info if device["id"] == mesh_device["switchID"])
                    created_device = create_device(matching_device, mesh_device, home["id"], self)

                    home_devices.append(created_device)

            room_json = []
            group_json = []
            if "groupsArray" in mesh_device_info:
                room_json = [group for group in mesh_device_info["groupsArray"] if group["isSubgroup"] == False]
                group_json = [group for group in mesh_device_info["groupsArray"] if group["isSubgroup"] == True]

            for group in group_json:
                group_devices = [device for device in home_devices if
                                 device.isolated_mesh_id in group.get("deviceIDArray", [])]
                groups.append(CyncGroup(group["displayName"], group["groupID"], group_devices))
                home_devices = [device for device in home_devices if device not in group_devices]

            for room in room_json:
                room_devices = [device for device in home_devices if device.isolated_mesh_id in room["deviceIDArray"]]
                room_groups = [group for group in groups if group.group_id in room.get("subgroupIDArray", [])]
                rooms.append(CyncRoom(room["displayName"], room["groupID"], room_groups, room_devices))
                home_devices = [device for device in home_devices if device not in room_devices]

            homes.append(CyncHome(home["name"], home["id"], rooms, home_devices))

        device_storage.set_user_homes(self._auth.user.user_id, homes)

    async def shut_down(self):
        await self._command_client.shut_down()

    async def set_device_power_state(self, device: CyncDevice, is_on: bool):
        await self._command_client.set_device_power_state(device, is_on)

    async def set_device_brightness(self, device: CyncDevice, brightness: int):
        await self._command_client.set_device_brightness(device, brightness)

    async def set_device_color_temp(self, device: CyncDevice, color_temp: int):
        await self._command_client.set_device_color_temp(device, color_temp)

    async def set_device_rgb(self, device: CyncDevice, rgb: tuple[int, int, int]):
        await self._command_client.set_device_rgb(device, rgb)

    def _start_command_client(self):
        self._command_client = CommandClient(self._auth.user)
