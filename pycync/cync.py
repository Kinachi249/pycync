"""
The main API interface for the Cync library.
Each instance of this class corresponds to one user, and all devices/homes associated with that user.
"""

import asyncio
from typing import Callable

from .auth import Auth
from .devices import create_device, CyncDevice
from .exceptions import MissingAuthError
from .const import REST_API_BASE_URL
from .groups import CyncRoom, CyncGroup, CyncHome
from .management.command_client import CommandClient
from .management import device_storage


class Cync:
    def __init__(self, auth: Auth):
        """
        Initialize a Cync object.
        The static create function should be used to create a new Cync object.
        """
        if not auth.user:
            raise MissingAuthError("No logged in user exists on auth object.")
        self._auth = auth
        self._command_client = CommandClient(auth.user)

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
        """
        Set the callback function that will be called when a device's state changes,
        or when a poll request for device state receives a response.
        """
        device_storage.set_user_device_callback(self._auth.user.user_id, update_callback)

    def update_device_states(self):
        """Query the server for current device states, and update the devices."""
        asyncio.create_task(self._command_client.update_mesh_devices())

    def get_devices(self):
        """Get a flat list of devices associated with this user."""
        return device_storage.get_flattened_devices(self._auth.user.user_id)

    def get_homes(self):
        """Get all homes, devices, and groups for the account."""
        return device_storage.get_user_homes(self._auth.user.user_id)

    async def refresh_home_info(self):
        """Refresh all nested home information for this account, and update the device storage.."""
        device_info = await self._auth._send_user_request(
            f"{REST_API_BASE_URL}/v2/user/{self._auth.user.user_id}/subscribe/devices")
        home_entries = [device for device in device_info if device["source"] == 5]
        homes = []

        for home in home_entries:
            home_devices: list[CyncDevice] = []
            rooms: list[CyncRoom] = []
            groups: list[CyncGroup] = []

            mesh_device_info = await self._auth._send_user_request(
                f"{REST_API_BASE_URL}/v2/product/{home["product_id"]}/device/{home["id"]}/property")
            if "bulbsArray" in mesh_device_info:
                mesh_devices = mesh_device_info["bulbsArray"]
                for mesh_device in mesh_devices:
                    matching_device = next(device for device in device_info if device["id"] == mesh_device["switchID"])
                    created_device = create_device(matching_device, mesh_device, home["id"], self._command_client)

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
        """Shut down the command client instance and close its associated connections."""
        await self._command_client.shut_down()

    def _start_command_client(self):
        """Start up the command client."""
        self._command_client.start_connection()
