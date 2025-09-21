"""
This TCP manager is responsible for maintaining the open TCP connection against the Cync server, and sending/receiving
packets associated with device events.
"""

from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING

import asyncio
import logging
import ssl
import struct
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

        self._packet_queue = asyncio.Queue()
        self._client_callback = client_callback

        self._login_acknowledged = False

        self._tcp_client_startup = asyncio.create_task(self._start_tcp_client())
        self._process_packet_task = None
        self._heartbeat_task = None
        self._transport = None
        self._protocol = None

    async def _start_tcp_client(self, delay_seconds: int | None = None):
        connected = False

        if delay_seconds:
            await asyncio.sleep(delay_seconds)

        while not connected:
            try:
                await self._establish_tcp_connection()
            except Exception:
                self._LOGGER.error("Failed to connect to Cync server. Retrying in 5 seconds...")
                await asyncio.sleep(5)
            else:
                connected = True

                self._process_packet_task = asyncio.create_task(self._process_packets(), name="Process Cync Packets")
                self._heartbeat_task = asyncio.create_task(self._send_pings(), name="Send Heartbeats")

                self._process_packet_task.add_done_callback(self._read_task_finished)

    async def _establish_tcp_connection(self):
        context = ssl.create_default_context()
        try:
            self._transport, self._protocol = await asyncio.get_event_loop().create_connection(lambda: CyncTcpProtocol(self._packet_queue, self._user), host=TCP_API_HOSTNAME, port=TCP_API_TLS_PORT, ssl=context)
        except Exception:
            # Normally this isn't something you'd want to do.
            # However, Cync's server has a 2+ year expired certificate and the common name doesn't match.
            # Why they haven't renewed/fixed it, and why their devices allow this, who knows...
            self._LOGGER.debug("Could not connect to Cync TCP server with strict TLS. Using relaxed TLS.")

            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self._transport, self._protocol = await asyncio.get_event_loop().create_connection(lambda: CyncTcpProtocol(self._packet_queue, self._user), host=TCP_API_HOSTNAME, port=TCP_API_TLS_PORT, ssl=context)

    async def _process_packets(self):
        """Process parsed packets as they're added to the async queue."""

        while True:
            parsed_packet = await self._packet_queue.get()

            match parsed_packet.message_type:
                case MessageType.LOGIN.value:
                    self._login_acknowledged = True
                case MessageType.DISCONNECT.value:
                    self._login_acknowledged = False
                    raise ConnectionClosedError

            await self._client_callback(parsed_packet)

    def _read_task_finished(self, future):
        self._transport.close()

        try:
            self._login_acknowledged = False
            self._heartbeat_task.cancel()
            future.result()
        except CancelledError:
            self._LOGGER.info("Cync client shutting down")
        except Exception as e:
            self._LOGGER.error("Cync server connection closed. Reconnecting in 10 seconds...")
            asyncio.create_task(self._start_tcp_client(10))

    async def _send_request(self, request):
        while not self._login_acknowledged:
            await asyncio.sleep(1)
            self._LOGGER.debug("Awaiting login acknowledge before sending request.")
        self._transport.write(request)

    async def _send_pings(self):
        """Periodically send a ping to the Cync server as a connection heartbeat."""

        while True:
            await asyncio.sleep(20)
            await self._send_request(bytes.fromhex('d300000000'))

    async def probe_devices(self, devices: list[CyncDevice]):
        """Probe all account devices to see which ones are responsive over Wi-Fi."""

        for device in devices:
            probe_device_packet = packet_builder.build_probe_request_packet(device.device_id)
            await self._send_request(probe_device_packet)

    async def shut_down(self):
        """Shut down the Cync client connection."""

        await self._send_request(bytes.fromhex('e30000000103'))
        self._process_packet_task.cancel()

    async def update_mesh_devices(self, hub_devices: list[CyncDevice]):
        """Get new device state."""
        for hub_device in hub_devices:
            state_request_packet = packet_builder.build_state_query_request_packet(hub_device.device_id)
            await self._send_request(state_request_packet)

    async def set_power_state(self, hub_device: CyncDevice, mesh_id: int, is_on: bool):
        """Set device(s) to either on or off."""
        request_packet = packet_builder.build_power_state_request_packet(hub_device.device_id, mesh_id, is_on)
        await self._send_request(request_packet)

    async def set_brightness(self, hub_device: CyncDevice, mesh_id: int, brightness: int):
        """Sets the brightness."""
        request_packet = packet_builder.build_brightness_request_packet(hub_device.device_id, mesh_id, brightness)
        await self._send_request(request_packet)

    async def set_color_temp(self, hub_device: CyncDevice, mesh_id: int, color_temp: int):
        """Sets the color temperature."""
        request_packet = packet_builder.build_color_temp_request_packet(hub_device.device_id, mesh_id, color_temp)
        await self._send_request(request_packet)

    async def set_rgb(self, hub_device: CyncDevice, mesh_id: int, rgb: tuple[int, int, int]):
        """Sets the RGB color."""
        request_packet = packet_builder.build_rgb_request_packet(hub_device.device_id, mesh_id, rgb)
        await self._send_request(request_packet)

class CyncTcpProtocol(asyncio.Protocol):
    """Protocol class for processing the Cync TCP packets."""

    _LOGGER = logging.getLogger(__name__)

    def __init__(self, packet_queue: asyncio.Queue, user):
        self._transport = None
        self._packet_queue = packet_queue
        self._user = user

    def connection_made(self, transport):
        self._transport = transport

        self._log_in()

    def data_received(self, data):
        while len(data) > 0:
            packet_length = struct.unpack(">I", data[1:5])[0]
            packet = data[:packet_length + 5]
            try:
                parsed_packet = packet_parser.parse_packet(packet, self._user.user_id)
                self._packet_queue.put_nowait(parsed_packet)
            except NotImplementedError:
                # Simply ignore the packet for now
                pass
            except Exception as ex:
                self._LOGGER.error("Unhandled exception while parsing packet: {}".format(str(ex)))
            finally:
                data = data[packet_length + 5:]

    def _log_in(self):
        login_request_packet = packet_builder.build_login_request_packet(self._user.authorize, self._user.user_id)
        self._transport.write(login_request_packet)

class ConnectionClosedError(Exception):
    """Connection closed error"""
