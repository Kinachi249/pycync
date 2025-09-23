"""
The proverbial "beating heart" of the Cync client.
This client listens for device state changes and updates them accordingly, and also handles sending all device action commands.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

import asyncio
import logging

from .packet import MessageType, ParsedMessage, PipeCommandCode
from .tcp_manager import TcpManager
from pycync.devices.controllable import CyncControllable
from pycync.exceptions import NoHubConnectedError, CyncError
from pycync.devices.capabilities import CyncCapability
from pycync.devices import device_storage
from pycync.user import User

if TYPE_CHECKING:
    from pycync.devices import CyncDevice
    from pycync.devices.groups import CyncHome


class CommandClient:
    _LOGGER = logging.getLogger(__name__)

    def __init__(self, user: User):
        self._user = user

        self._device_statuses_updated = False
        self._tcp_manager: TcpManager = None

    def start_connection(self):
        self._tcp_manager = TcpManager(self._user, self.on_message_received)

    async def on_message_received(self, parsed_message: ParsedMessage):
        match parsed_message.message_type:
            case MessageType.LOGIN.value:
                await self.probe_devices()
            case MessageType.PROBE.value if parsed_message.version != 0:
                devices_in_home = device_storage.get_associated_home_devices(self._user.user_id,
                                                                             parsed_message.device_id)
                device = next(device for device in devices_in_home if device.device_id == parsed_message.device_id)
                device.set_wifi_connected(True)
                self._device_statuses_updated = True
            case MessageType.SYNC.value:
                await self._send_update_to_listener(parsed_message.data)
            case MessageType.PIPE.value:
                if parsed_message.command_code == PipeCommandCode.QUERY_DEVICE_STATUS_PAGES.value:
                    updated_devices: dict[int, CyncDevice] = parsed_message.data
                    for device in device_storage.get_flattened_devices(self._user.user_id):
                        device.is_online = device.device_id in updated_devices
                    await self._send_update_to_listener(parsed_message.data)

    async def probe_devices(self):
        await self._tcp_manager.probe_devices(device_storage.get_flattened_devices(self._user.user_id))

    async def update_mesh_devices(self):
        """Get new device state."""
        homes_for_user = device_storage.get_user_homes(self._user.user_id)

        hub_devices: list[CyncDevice] = []
        for home in homes_for_user:
            hub_device = await self._fetch_hub_device(home)
            hub_devices.append(hub_device)

        await self._tcp_manager.update_mesh_devices(hub_devices)

    async def set_power_state(self, controllable: CyncControllable, is_on: bool):
        """Set device(s) to either on or off."""
        associated_home = device_storage.get_home_by_id(self._user.user_id, controllable.parent_home_id)
        hub_device = await self._fetch_hub_device(associated_home)

        await self._tcp_manager.set_power_state(hub_device, controllable.mesh_reference_id, is_on)

    async def set_brightness(self, controllable: CyncControllable, brightness: int):
        """Sets the brightness. Must be between 0 and 100 inclusive."""
        if brightness < 0 or brightness > 100:
            raise CyncError("Brightness must be between 0 and 100 inclusive")

        associated_home = device_storage.get_home_by_id(self._user.user_id, controllable.parent_home_id)
        hub_device = await self._fetch_hub_device(associated_home)

        await self._tcp_manager.set_brightness(hub_device, controllable.mesh_reference_id, brightness)

    async def set_color_temp(self, controllable: CyncControllable, color_temp: int):
        """
        Sets the color temperature. Must be between 1 and 100 inclusive.
        1 represents the most "blue" and 100 represents the most "orange".
        """
        if color_temp < 1 or color_temp > 100:
            raise CyncError("Color temperature must be between 1 and 100 inclusive.")

        associated_home = device_storage.get_home_by_id(self._user.user_id, controllable.parent_home_id)
        hub_device = await self._fetch_hub_device(associated_home)

        await self._tcp_manager.set_color_temp(hub_device, controllable.mesh_reference_id, color_temp)

    async def set_rgb(self, controllable: CyncControllable, rgb: tuple[int, int, int]):
        """Sets the RGB color. Each color must be between 0 and 255 inclusive."""
        if rgb[0] > 255 or rgb[1] > 255 or rgb[2] > 255:
            raise CyncError("Each RGB value must be between 0 and 255 inclusive")

        associated_home = device_storage.get_home_by_id(self._user.user_id, controllable.parent_home_id)
        hub_device = await self._fetch_hub_device(associated_home)

        await self._tcp_manager.set_rgb(hub_device, controllable.mesh_reference_id, rgb)

    async def shut_down(self):
        await self._tcp_manager.shut_down()

    async def _send_update_to_listener(self, updated_data: dict[int, CyncDevice]):
        callback = device_storage.get_user_device_callback(self._user.user_id)
        if callback is not None:
            if asyncio.iscoroutinefunction(callback):
                await callback(updated_data)
            else:
                callback(updated_data)

    async def _fetch_hub_device(self, home: CyncHome) -> CyncDevice:
        """
        Fetches an eligible 'hub device' from a given home.
        A hub device is a device that is actively connected to Wi-Fi, and can act as a proxy into the Bluetooth mesh.
        """

        while not self._device_statuses_updated:
            await asyncio.sleep(1)
            self._LOGGER.debug("Awaiting probe initialization before fetching hub.")

        hub_device = next((device for device in home.get_flattened_device_list() if
                           device.wifi_connected and CyncCapability.SIG_MESH in device.capabilities), None)
        if hub_device is None:
            raise NoHubConnectedError

        return hub_device
