import asyncio
import logging
import ssl
import struct
import threading
from typing import Any, Callable

from pycync import CyncDevice, User
from pycync.devices import CyncLight

from .packet_parser import PacketParser
from pycync.management import packet_builder as PacketBuilder
from .const import MessageType, PipeCommandCode
from ..exceptions import NoHubConnectedError, CyncError


class CommandClient:
    _LOGGER = logging.getLogger(__name__)

    def __init__(self, devices: list[CyncDevice], user: User, on_data_update: Callable[[dict[str, Any]], None]):
        self._devices = devices
        self._user = user
        self._on_data_update = on_data_update
        self._packet_parser = PacketParser(self._devices)

        self._client_closed = False
        self._loop = None
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
                    self.reader, self.writer = await asyncio.open_connection('cm.gelighting.com', 23779, ssl=context)
                except Exception as e:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    try:
                        self.reader, self.writer = await asyncio.open_connection('cm.gelighting.com', 23779,
                                                                                 ssl=context)
                    except Exception as e:
                        self.reader, self.writer = await asyncio.open_connection('cm.gelighting.com', 23778)
            except Exception as e:
                self._LOGGER.error(e)
                await asyncio.sleep(5)
            else:
                await self._log_in()
                await self._probe_devices()

                read_tcp_messages = asyncio.create_task(self._read_packets(), name="Read TCP Messages")
                maintain_connection = asyncio.create_task(self._send_pings(), name="Maintain Connection")
                read_write_tasks = [read_tcp_messages, maintain_connection]
                try:
                    done, pending = await asyncio.wait(read_write_tasks, return_when=asyncio.FIRST_EXCEPTION)
                    for task in done:
                        name = task.get_name()
                        exception = task.exception()
                        try:
                            result = task.result()
                        except Exception as e:
                            self._LOGGER.error(e)
                    for task in pending:
                        task.cancel()
                    if not self._client_closed:
                        self._LOGGER.info("Connection to Cync server reset, restarting in 15 seconds")
                        await asyncio.sleep(15)
                    else:
                        self._LOGGER.info("Cync client shutting down")
                except Exception as e:
                    self._LOGGER.error(e)

    async def _log_in(self):
        login_request_packet = PacketBuilder.build_login_request_packet(self._user.authorize, self._user.user_id)
        self.writer.write(login_request_packet)
        await self.writer.drain()

    async def _probe_devices(self):
        for device in self._devices:
            probe_device_packet = PacketBuilder.build_probe_request_packet(device.device_id)
            self.writer.write(probe_device_packet)
            await self.writer.drain()

    async def _read_packets(self):
        while not self._client_closed:
            data = await self.reader.read(1500)
            if len(data) == 0:
                self.logged_in = False
                raise ConnectionClosedError
            while data:
                packet_length = struct.unpack(">I", data[1:5])[0]
                packet = data[:packet_length + 5]
                try:
                    parsed_packet = self._packet_parser.parse_packet(packet)
                except NotImplementedError:
                    # Simply ignore the packet for now
                    data = data[packet_length + 5:]
                    continue

                match parsed_packet.message_type:
                    case MessageType.PROBE.value if parsed_packet.version != 0:
                        device = next(device for device in self._devices if device.device_id == parsed_packet.device_id)
                        device.set_wifi_connected(True)
                    case MessageType.SYNC.value:
                        self._on_data_update(parsed_packet.data)
                    case MessageType.PIPE.value:
                        if parsed_packet.command_code == PipeCommandCode.QUERY_DEVICE_STATUS_PAGES.value:
                            self._on_data_update(parsed_packet.data)

                data = data[packet_length + 5:]

        raise ShuttingDown

    async def _send_pings(self):
        while not self._client_closed:
            await asyncio.sleep(20)
            self.writer.write(bytes.fromhex('d300000000'))
            await self.writer.drain()
        raise ShuttingDown

    async def update_mesh_devices(self):
        """Get new device state."""
        hub_device = self._fetch_hub_device()

        device_id = hub_device.device_id
        state_request_packet = PacketBuilder.build_state_query_request_packet(device_id)
        self._loop.call_soon_threadsafe(self._send_request, state_request_packet)

    async def set_device_power_state(self, device, is_on: bool):
        hub_device = self._fetch_hub_device()

        request_packet = PacketBuilder.build_power_state_request_packet(hub_device.device_id, device.isolated_mesh_id, is_on)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    async def set_device_brightness(self, device, brightness: int):
        if brightness < 0 or brightness > 100:
            raise CyncError()

        hub_device = self._fetch_hub_device()

        request_packet = PacketBuilder.build_brightness_request_packet(hub_device.device_id, device.isolated_mesh_id, brightness)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    async def set_device_color_temp(self, device, color_temp):
        if color_temp < 1 or color_temp > 100:
            raise CyncError()

        hub_device = self._fetch_hub_device()

        request_packet = PacketBuilder.build_color_temp_request_packet(hub_device.device_id, device.isolated_mesh_id, color_temp)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    async def set_device_rgb(self, device, rgb: tuple[int, int, int]):
        if rgb[0] > 255 or rgb[1] > 255 or rgb[2] > 255:
            raise CyncError()

        hub_device = self._fetch_hub_device()

        request_packet = PacketBuilder.build_rgb_request_packet(hub_device.device_id, device.isolated_mesh_id, rgb)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    def _fetch_hub_device(self):
        hub_device = next((device for device in self._devices if device.wifi_connected and isinstance(device, CyncLight)), None)
        if hub_device is None:
            raise NoHubConnectedError()

        return hub_device

    def _send_request(self, request):
        async def send():
            self.writer.write(request)
            await self.writer.drain()

        self._loop.create_task(send())

class ConnectionClosedError(Exception):
    """Connection closed error"""

class ShuttingDown(Exception):
    """Cync client shutting down"""
