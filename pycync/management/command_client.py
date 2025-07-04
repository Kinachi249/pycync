import asyncio
import logging
import ssl
import struct
import threading

from pycync import CyncDevice, User

from pycync.management import packet_builder as PacketBuilder


class CommandClient:
    _LOGGER = logging.getLogger(__name__)

    def __init__(self, devices: list[CyncDevice], user: User):
        self._devices = devices
        self._user = user

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

    async def _read_packets(self):
        while not self._client_closed:
            data = await self.reader.read(1500)
            if len(data) == 0:
                self.logged_in = False
                raise ConnectionClosedError
            while len(data) > 0:
                packet_type = int(data[0])
                packet_length = struct.unpack(">I", data[1:5])[0]
                print(f"Packet type {packet_type}, packet length {packet_length}")
                print(f"{data[:packet_length + 5]}")
                data = data[packet_length + 5:]

        raise ShuttingDown

    async def _send_pings(self):
        while not self._client_closed:
            await asyncio.sleep(20)
            self.writer.write(bytes.fromhex('d300000000'))
            await self.writer.drain()
        raise ShuttingDown

    async def update_devices(self):
        """Get new device state."""
        for device in self._devices:
            device_id = device.device_id
            state_request_packet = PacketBuilder.build_probe_request_packet(device_id)
            self._loop.call_soon_threadsafe(self._send_request, state_request_packet)
            await asyncio.sleep(1)

    def _send_request(self, request):
        async def send():
            self.writer.write(request)
            await self.writer.drain()

        self._loop.create_task(send())

class ConnectionClosedError(Exception):
    """Connection closed error"""

class ShuttingDown(Exception):
    """Cync client shutting down"""
