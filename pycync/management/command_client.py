"""
The proverbial "beating heart" of the Cync client.
This TCP client will retain an open connection the same way that the Cync app does.
It listens for device state changes and updates them accordingly, and also handles sending all device action commands.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

import asyncio
import logging
import ssl
import struct
import threading

from . import packet_parser
from .tcp_constants import MessageType, PipeCommandCode
from ..const import TCP_API_HOSTNAME, TCP_API_TLS_PORT, TCP_API_UNSECURED_PORT
from ..exceptions import NoHubConnectedError, CyncError
from ..management import device_storage, packet_builder
from ..mappings.capabilities import CyncCapability
from ..user import User

if TYPE_CHECKING:
    from ..devices import CyncDevice
    from ..groups import CyncHome


class CommandClient:
    _LOGGER = logging.getLogger(__name__)

    def __init__(self, user: User):
        self._user = user

        self._client_closed = False
        self._login_acknowledged = False
        self._probe_completed = False
        self._loop = None
        self._client_thread = None
        self.reader = None
        self.writer = None

    def start_connection(self):
        self._client_thread = threading.Thread(target=self._open_thread_connection, daemon=True)
        self._client_thread.start()

    def _open_thread_connection(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._begin_client_loop())

    async def _begin_client_loop(self):
        while not self._client_closed:
            try:
                context = ssl.create_default_context()
                try:
                    self.reader, self.writer = await asyncio.open_connection(TCP_API_HOSTNAME, TCP_API_TLS_PORT, ssl=context)
                except Exception as e:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    try:
                        self.reader, self.writer = await asyncio.open_connection(TCP_API_HOSTNAME, TCP_API_TLS_PORT, ssl=context)
                    except Exception as e:
                        self.reader, self.writer = await asyncio.open_connection(TCP_API_HOSTNAME, TCP_API_UNSECURED_PORT)
            except Exception as e:
                self._LOGGER.error(e)
                await asyncio.sleep(5)
            else:
                await self._log_in()

                read_tcp_messages = asyncio.create_task(self._read_packets(), name="Read TCP Messages")
                maintain_connection = asyncio.create_task(self._send_pings(), name="Maintain Connection")
                read_write_tasks = [read_tcp_messages, maintain_connection]
                try:
                    done, pending = await asyncio.wait(read_write_tasks, return_when=asyncio.FIRST_EXCEPTION)
                    for task in done:
                        try:
                            result = task.result()
                        except ShuttingDown:
                            self._LOGGER.info("Cync client shutting down")
                        except Exception as e:
                            self._LOGGER.error(e)
                    for task in pending:
                        task.cancel()
                    if not self._client_closed:
                        self._LOGGER.info("Connection to Cync server reset, restarting in 15 seconds")
                        await asyncio.sleep(15)

                except Exception as e:
                    self._LOGGER.error(e)

    async def _log_in(self):
        login_request_packet = packet_builder.build_login_request_packet(self._user.authorize, self._user.user_id)
        self.writer.write(login_request_packet)
        await self.writer.drain()

    async def _probe_devices(self):
        for device in device_storage.get_flattened_devices(self._user.user_id):
            probe_device_packet = packet_builder.build_probe_request_packet(device.device_id)
            self.writer.write(probe_device_packet)
            await self.writer.drain()

    async def _read_packets(self):
        while not self._client_closed:
            data = await self.reader.read(1500)
            while data:
                packet_length = struct.unpack(">I", data[1:5])[0]
                packet = data[:packet_length + 5]
                try:
                    parsed_packet = packet_parser.parse_packet(packet, self._user.user_id)
                except NotImplementedError:
                    # Simply ignore the packet for now
                    data = data[packet_length + 5:]
                    continue

                match parsed_packet.message_type:
                    case MessageType.LOGIN.value:
                        self._login_acknowledged = True
                        await self._probe_devices()
                    case MessageType.PROBE.value if parsed_packet.version != 0:
                        devices_in_home = device_storage.get_associated_home_devices(self._user.user_id, parsed_packet.device_id)
                        device = next(device for device in devices_in_home if device.device_id == parsed_packet.device_id)
                        device.set_wifi_connected(True)
                        self._probe_completed = True
                    case MessageType.SYNC.value:
                        callback = device_storage.get_user_device_callback(self._user.user_id)
                        if callback is not None:
                            callback(parsed_packet.data)
                    case MessageType.PIPE.value:
                        if parsed_packet.command_code == PipeCommandCode.QUERY_DEVICE_STATUS_PAGES.value:
                            callback = device_storage.get_user_device_callback(self._user.user_id)
                            if callback is not None:
                                callback(parsed_packet.data)
                    case MessageType.DISCONNECT.value:
                        self._login_acknowledged = False
                        raise ConnectionClosedError

                data = data[packet_length + 5:]

        raise ShuttingDown

    async def _send_pings(self):
        while not self._client_closed:
            await asyncio.sleep(20)
            self.writer.write(bytes.fromhex('d300000000'))
            await self.writer.drain()
        raise ShuttingDown

    async def shut_down(self):
        self._client_closed = True
        self.writer.write(bytes.fromhex('e30000000103'))
        await self.writer.drain()

    async def update_mesh_devices(self):
        """Get new device state."""
        homes_for_user = device_storage.get_user_homes(self._user.user_id)

        for home in homes_for_user:
            hub_device = await self._fetch_hub_device(home)
            state_request_packet = packet_builder.build_state_query_request_packet(hub_device.device_id)
            self._loop.call_soon_threadsafe(self._send_request, state_request_packet)

    async def set_device_power_state(self, device: CyncDevice, is_on: bool):
        """Set a device to either on or off."""
        device_home = device_storage.get_associated_home(self._user.user_id, device.device_id)
        hub_device = await self._fetch_hub_device(device_home)

        request_packet = packet_builder.build_power_state_request_packet(hub_device.device_id, device.isolated_mesh_id, is_on)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    async def set_device_brightness(self, device: CyncDevice, brightness: int):
        """Sets the brightness of a device. Must be between 0 and 100 inclusive."""
        if brightness < 0 or brightness > 100:
            raise CyncError()

        device_home = device_storage.get_associated_home(self._user.user_id, device.device_id)
        hub_device = await self._fetch_hub_device(device_home)

        request_packet = packet_builder.build_brightness_request_packet(hub_device.device_id, device.isolated_mesh_id, brightness)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    async def set_device_color_temp(self, device: CyncDevice, color_temp: int):
        """
        Sets the color temperature of a device. Must be between 1 and 100 inclusive.
        1 represents the most "blue" and 100 represents the most "orange".
        """
        if color_temp < 1 or color_temp > 100:
            raise CyncError()

        device_home = device_storage.get_associated_home(self._user.user_id, device.device_id)
        hub_device = await self._fetch_hub_device(device_home)

        request_packet = packet_builder.build_color_temp_request_packet(hub_device.device_id, device.isolated_mesh_id, color_temp)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    async def set_device_rgb(self, device: CyncDevice, rgb: tuple[int, int, int]):
        """Sets the RGB color of a device. Each color must be between 0 and 255 inclusive."""
        if rgb[0] > 255 or rgb[1] > 255 or rgb[2] > 255:
            raise CyncError()

        device_home = device_storage.get_associated_home(self._user.user_id, device.device_id)
        hub_device = await self._fetch_hub_device(device_home)

        request_packet = packet_builder.build_rgb_request_packet(hub_device.device_id, device.isolated_mesh_id, rgb)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    async def _fetch_hub_device(self, home: CyncHome) -> CyncDevice:
        while not self._probe_completed:
            await asyncio.sleep(1)
            self._LOGGER.debug("Awaiting probe initialization before fetching hub.")

        hub_device = next((device for device in home.get_flattened_device_list() if device.wifi_connected and CyncCapability.SIG_MESH in device.capabilities), None)
        if hub_device is None:
            raise NoHubConnectedError

        return hub_device

    def _send_request(self, request):
        async def send():
            self.writer.write(request)
            await self.writer.drain()

        while not self._login_acknowledged:
            asyncio.sleep(1)
            self._LOGGER.debug("Awaiting login acknowledge before sending request.")
        self._loop.create_task(send())

class ConnectionClosedError(Exception):
    """Connection closed error"""

class ShuttingDown(Exception):
    """Cync client shutting down"""
