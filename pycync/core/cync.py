import asyncio
from typing import Callable, Any

from pycync import Auth
from pycync.devices import create_device, CyncDevice
from pycync.exceptions import MissingAuthError
from pycync.const import REST_API_BASE_URL
from pycync.management.command_client import CommandClient


class Cync:
    """Docs."""
    def __init__(self, auth: Auth):
        """Initialize the Cync object."""
        if not auth.user:
            raise MissingAuthError("No logged in user exists on auth object.")
        self._auth = auth
        self._command_client = None

    def get_logged_in_user(self):
        """Get logged in user."""

        return self._auth.user

    async def track_devices(self, devices: list[CyncDevice], on_data_update: Callable[[dict[str, Any]], None]):
        """Track devices."""
        self._command_client = CommandClient(devices, self._auth.user, on_data_update)
        await asyncio.sleep(0.5)

    def update_device_states(self):
        """Update device states."""
        asyncio.create_task(self._command_client.update_mesh_devices())

    async def get_device_list(self):
        """Get list of devices."""
        devices: list[CyncDevice] = []
        device_info = await self._auth.send_user_request(f"{REST_API_BASE_URL}/v2/user/{self._auth.user.user_id}/subscribe/devices")
        home_entries = [device for device in device_info if device["source"] == 5]
        for home in home_entries:
            mesh_device_info = await self._auth.send_user_request(f"{REST_API_BASE_URL}/v2/product/{home["product_id"]}/device/{home["id"]}/property")
            if "bulbsArray" in mesh_device_info:
                mesh_devices = mesh_device_info["bulbsArray"]
                for mesh_device in mesh_devices:
                    matching_device = next(device for device in device_info if device["id"] == mesh_device["switchID"])
                    created_device = create_device(matching_device, mesh_device, home["id"], self)

                    await self._auth.async_login_device(created_device)
                    devices.append(created_device)

        # Provide online devices first, so that later offline devices will be able
        # to check the online devices for their mesh state.
        return sorted(devices, key=lambda device: device.is_online, reverse=True)

    async def set_device_power_state(self, device: CyncDevice, is_on: bool):
        await self._command_client.set_device_power_state(device, is_on)

    async def set_device_brightness(self, device: CyncDevice, brightness: int):
        await self._command_client.set_device_brightness(device, brightness)

    async def set_device_color_temp(self, device: CyncDevice, color_temp: int):
        await self._command_client.set_device_color_temp(device, color_temp)

    async def set_device_rgb(self, device: CyncDevice, rgb: tuple[int, int, int]):
        await self._command_client.set_device_rgb(device, rgb)

    async def update_device_datapoints(self, device: CyncDevice):
        datapoints = await self._auth.send_device_request(device,f"{REST_API_BASE_URL}/v2/product/{device.product_id}/datapoints")
        datapoint_values = await self._auth.send_device_request(device, f"{REST_API_BASE_URL}/v2/product/{device.product_id}/v_device/{device.device_id}")
        device_datapoint_data = {}
        for datapoint in [datapoint for datapoint in datapoints if str(datapoint["index"]) in datapoint_values]:
            name = datapoint["field_name"]
            value = datapoint_values[str(datapoint["index"])]
            device_datapoint_data[name] = {"index": datapoint["index"], "value": value}
        device.set_datapoints(device_datapoint_data)