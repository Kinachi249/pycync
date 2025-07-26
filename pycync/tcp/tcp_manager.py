from __future__ import annotations
from typing import TYPE_CHECKING

import asyncio
import logging
import ssl
import struct
import threading
from typing import Callable

from pycync import User
from . import packet_builder, packet_parser
from .packet import MessageType

if TYPE_CHECKING:
    from pycync.devices import CyncDevice

TCP_API_HOSTNAME = "cm-sec.gelighting.com"
TCP_API_TLS_PORT = 23779

class TcpManager:
    _LOGGER = logging.getLogger(__name__)

    def __init__(self, user: User, client_callback: Callable):
        self._user = user

        self._client_closed = False
        self._login_acknowledged = False
        self._loop = None
        self._client_thread = threading.Thread(target=self._open_thread_connection, daemon=True)
        self.reader = None
        self.writer = None
        self.client_callback = client_callback

        self._client_thread.start()

    def _open_thread_connection(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._begin_client_loop())

    async def _begin_client_loop(self):
        while not self._client_closed:
            try:
                await self._establish_tcp_connection()
            except Exception:
                self._LOGGER.error("Failed to connect to Cync server. Retrying in 5 seconds...")
                await asyncio.sleep(5)
            else:
                await self._log_in()

                read_tcp_messages = asyncio.create_task(self._read_packets(), name="Read TCP Messages")
                heartbeat_task = asyncio.create_task(self._send_pings(), name="Send Heartbeats")
                read_write_tasks = [read_tcp_messages, heartbeat_task]
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
                        self._LOGGER.info("Cync server connection closed. Reconnecting in 10 seconds...")
                        await asyncio.sleep(10)

                except Exception as e:
                    self._LOGGER.error(e)

    async def _establish_tcp_connection(self):
        context = ssl.create_default_context()
        try:
            self.reader, self.writer = await asyncio.open_connection(TCP_API_HOSTNAME, TCP_API_TLS_PORT, ssl=context)
        except Exception:
            # Normally this isn't something you'd want to do.
            # However, Cync's server has a 2+ year expired certificate and the common name doesn't match.
            # Why they haven't renewed/fixed it, and why their devices allow this, who knows...
            self._LOGGER.debug("Could not connect to TCP server with strict TLS. Using relaxed TLS.")

            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.reader, self.writer = await asyncio.open_connection(TCP_API_HOSTNAME, TCP_API_TLS_PORT, ssl=context)

    async def _log_in(self):
        login_request_packet = packet_builder.build_login_request_packet(self._user.authorize, self._user.user_id)
        self.writer.write(login_request_packet)
        await self.writer.drain()

    def probe_devices(self, devices: list[CyncDevice]):
        for device in devices:
            probe_device_packet = packet_builder.build_probe_request_packet(device.device_id)
            self._loop.call_soon_threadsafe(self._send_request, probe_device_packet)

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
                    case MessageType.DISCONNECT.value:
                        self._login_acknowledged = False
                        raise ConnectionClosedError

                self.client_callback(parsed_packet)

                data = data[packet_length + 5:]

        raise ShuttingDown

    async def _send_pings(self):
        while not self._client_closed:
            await asyncio.sleep(20)
            self._loop.call_soon_threadsafe(self._send_request, bytes.fromhex('d300000000'))
        raise ShuttingDown

    def shut_down(self):
        self._client_closed = True
        self._send_request(bytes.fromhex('e30000000103'))

    def update_mesh_devices(self, hub_devices: list[CyncDevice]):
        """Get new device state."""
        for hub_device in hub_devices:
            state_request_packet = packet_builder.build_state_query_request_packet(hub_device.device_id)
            self._loop.call_soon_threadsafe(self._send_request, state_request_packet)

    def set_power_state(self, hub_device: CyncDevice, mesh_id: int, is_on: bool):
        """Set device(s) to either on or off."""
        request_packet = packet_builder.build_power_state_request_packet(hub_device.device_id, mesh_id, is_on)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    def set_brightness(self, hub_device: CyncDevice, mesh_id: int, brightness: int):
        """Sets the brightness."""
        request_packet = packet_builder.build_brightness_request_packet(hub_device.device_id, mesh_id, brightness)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    def set_color_temp(self, hub_device: CyncDevice, mesh_id: int, color_temp: int):
        """Sets the color temperature."""
        request_packet = packet_builder.build_color_temp_request_packet(hub_device.device_id, mesh_id, color_temp)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    def set_rgb(self, hub_device: CyncDevice, mesh_id: int, rgb: tuple[int, int, int]):
        """Sets the RGB color."""
        request_packet = packet_builder.build_rgb_request_packet(hub_device.device_id, mesh_id, rgb)
        self._loop.call_soon_threadsafe(self._send_request, request_packet)

    def _send_request(self, request):
        async def send():
            while not self._login_acknowledged:
                await asyncio.sleep(1)
                self._LOGGER.debug("Awaiting login acknowledge before sending request.")
            self.writer.write(request)
            await self.writer.drain()

        self._loop.create_task(send())

class ConnectionClosedError(Exception):
    """Connection closed error"""

class ShuttingDown(Exception):
    """Cync client shutting down"""
