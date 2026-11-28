"""
Bluetooth manager for controlling Cync devices directly over Telink Bluetooth mesh using telinkbt.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, TYPE_CHECKING

import telinkbt

from pycync.devices.device_types import DeviceType
from pycync.tcp.packet import PipeCommandCode

if TYPE_CHECKING:
    from pycync.devices import CyncDevice
    from pycync.devices.groups import CyncHome

TELINK_VENDOR_ID = 0x0211
TELINK_BROADCAST_ADDRESS = 0xFFFF
TELINK_STATUS_QUERY_COMMAND = 0xDA
TELINK_STATUS_NOTIFY_COMMAND = 0xDC
DEFAULT_RECONNECT_COOLDOWN_SECONDS = 60.0


class BluetoothManager:
    """Manages Telink BLE mesh connections per CyncHome using telinkbt."""

    _LOGGER = logging.getLogger(__name__)

    def __init__(
        self,
        update_callback: Callable | None = None,
        reconnect_cooldown: float = DEFAULT_RECONNECT_COOLDOWN_SECONDS
    ):
        self._update_callback = update_callback
        self._reconnect_cooldown = reconnect_cooldown
        self._mesh_links: dict[int, telinkbt.telinkbt] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self._unavailable_until: dict[int, float] = {}

    def _get_lock(self, home_id: int) -> asyncio.Lock:
        lock = self._locks.get(home_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[home_id] = lock
        return lock

    def is_home_connected(self, home_id: int) -> bool:
        """Return True if there is an active BLE connection for the given home."""
        link = self._mesh_links.get(home_id)
        return link is not None and link.client is not None and link.client.is_connected

    async def connect_home(self, home: CyncHome) -> bool:
        """
        Attempt to connect to a home's Telink Bluetooth mesh by trying each device
        with a BLE MAC address in turn. Returns True if connected, False otherwise.
        """
        async with self._get_lock(home.home_id):
            return await self._connect_home_unlocked(home)

    async def _connect_home_unlocked(self, home: CyncHome) -> bool:
        if self.is_home_connected(home.home_id):
            return True

        if not home.mesh_address or not home.mesh_password:
            self._LOGGER.debug(
                "Home %s (%s) does not have mesh credentials for Bluetooth.",
                home.name,
                home.home_id,
            )
            return False

        macs: list[str] = []
        seen_macs: set[str] = set()
        for device in home.get_flattened_device_list():
            if device.mac and device.mac not in seen_macs:
                seen_macs.add(device.mac)
                macs.append(device.mac)

        if not macs:
            self._LOGGER.debug(
                "Home %s (%s) has no devices with MAC addresses.",
                home.name,
                home.home_id,
            )
            return False

        for mac in macs:
            try:
                link = telinkbt.telinkbt(
                    TELINK_VENDOR_ID,
                    mac,
                    home.mesh_address,
                    home.mesh_password,
                    mesh=home,
                    callback=self._on_notification
                )
                await link.connect()
                self._mesh_links[home.home_id] = link
                self._unavailable_until.pop(home.home_id, None)
                self._LOGGER.debug(
                    "Connected to Bluetooth mesh for home %s (%s) via %s.",
                    home.name,
                    home.home_id,
                    mac,
                )
                return True
            except Exception as err:
                self._LOGGER.debug(
                    "Failed to connect via Bluetooth to %s for home %s: %s (%s)",
                    mac,
                    home.home_id,
                    err,
                    err.__cause__,
                )

        self._mesh_links.pop(home.home_id, None)
        self._unavailable_until[home.home_id] = time.monotonic() + self._reconnect_cooldown
        return False

    async def _disconnect_home_unlocked(self, home_id: int):
        link = self._mesh_links.pop(home_id, None)
        if link is not None:
            try:
                await link.disconnect()
            except Exception as err:
                self._LOGGER.debug("Error disconnecting Bluetooth link for home %s: %s", home_id, err)

    async def _send_command(self, home: CyncHome, target: int, command: int, data: list[int]) -> bool:
        """
        Send a Telink mesh command over Bluetooth for the given home.
        Returns True if sent successfully, False if Bluetooth is unavailable or failed.
        """
        async with self._get_lock(home.home_id):
            if not self.is_home_connected(home.home_id):
                unavailable_until = self._unavailable_until.get(home.home_id, 0.0)
                if time.monotonic() < unavailable_until:
                    return False
                if not await self._connect_home_unlocked(home):
                    return False

            link = self._mesh_links.get(home.home_id)
            if link is None:
                return False

            try:
                await link.send_packet(target, command, data)
                return True
            except Exception as err:
                self._LOGGER.debug(
                    "Bluetooth command 0x%02x failed for home %s: %s",
                    command,
                    home.home_id,
                    err,
                )
                await self._disconnect_home_unlocked(home.home_id)
                self._unavailable_until[home.home_id] = time.monotonic() + self._reconnect_cooldown
                return False

    async def update_mesh_devices(self, home: CyncHome) -> bool:
        """Broadcast a status query to all devices in the home's Bluetooth mesh."""
        return await self._send_command(home, TELINK_BROADCAST_ADDRESS, TELINK_STATUS_QUERY_COMMAND, [])

    async def set_power_state(self, home: CyncHome, mesh_id: int, mesh_group_id: int, is_on: bool) -> bool:
        """Set device or group power state over Bluetooth."""
        if mesh_group_id > 0:
            target = ((mesh_group_id & 0xFF) << 8) | (mesh_id & 0xFF)
        else:
            target = mesh_id & 0xFFFF
        return await self._send_command(
            home,
            target,
            PipeCommandCode.SET_POWER_STATE.value,
            [int(is_on)]
        )

    async def set_brightness(self, home: CyncHome, mesh_id: int, brightness: int) -> bool:
        """Set device or group brightness (0-100) over Bluetooth."""
        return await self._send_command(
            home,
            mesh_id & 0xFFFF,
            PipeCommandCode.SET_BRIGHTNESS.value,
            [brightness]
        )

    async def set_color_temp(self, home: CyncHome, mesh_id: int, color_temp: int) -> bool:
        """Set device or group color temperature (1-100) over Bluetooth."""
        return await self._send_command(
            home,
            mesh_id & 0xFFFF,
            PipeCommandCode.SET_COLOR.value,
            [0x05, color_temp]
        )

    async def set_rgb(self, home: CyncHome, mesh_id: int, rgb: tuple[int, int, int]) -> bool:
        """Set device or group RGB color over Bluetooth."""
        return await self._send_command(
            home,
            mesh_id & 0xFFFF,
            PipeCommandCode.SET_COLOR.value,
            [0x04, rgb[0], rgb[1], rgb[2]]
        )

    async def set_combo(
        self,
        home: CyncHome,
        mesh_id: int,
        is_on: bool,
        brightness: int,
        color_temp: int | None,
        rgb: tuple[int, int, int] | None
    ) -> bool:
        """Set power, brightness, and color in a single Telink mesh command."""
        if color_temp is not None:
            color_mode = color_temp
            rgb_vals = [0, 0, 0]
        elif rgb is not None:
            color_mode = 0xFE
            rgb_vals = [rgb[0], rgb[1], rgb[2]]
        else:
            color_mode = 0xFF
            rgb_vals = [0, 0, 0]

        data = [int(is_on), brightness, color_mode, *rgb_vals]
        return await self._send_command(
            home,
            mesh_id & 0xFFFF,
            PipeCommandCode.COMBO_CONTROL.value,
            data
        )

    async def _on_notification(self, home: CyncHome, data: list[int]):
        """Handle decrypted Telink mesh status notifications (opcode 0xdc)."""
        if len(data) < 18 or data[7] != TELINK_STATUS_NOTIFY_COMMAND:
            return

        responses = data[10:18]
        device_list = home.get_flattened_device_list()
        updated_devices: dict[str, CyncDevice] = {}

        for i in (0, 4):
            response = responses[i:i + 4]
            mesh_id = response[0]
            if mesh_id == 0:
                continue

            resolved_devices = [device for device in device_list if device.isolated_mesh_id == mesh_id]
            if not resolved_devices:
                continue

            if DeviceType.is_light(resolved_devices[0].device_type_id):
                raw_brightness = response[2]
                if raw_brightness >= 128:
                    brightness = raw_brightness - 128
                    red = int(((response[3] & 0xE0) >> 5) * 255 / 7)
                    green = int(((response[3] & 0x1C) >> 2) * 255 / 7)
                    blue = int((response[3] & 0x03) * 255 / 3)
                    color_temp = 0xFE
                    rgb = (red, green, blue)
                else:
                    brightness = raw_brightness
                    color_temp = response[3]
                    rgb = (0, 0, 0)
                is_on = brightness > 0
                for device in resolved_devices:
                    device.update_state(is_on, brightness, color_temp, rgb, is_online=True)
                    updated_devices[device.unique_id] = device
            elif DeviceType.is_plug(resolved_devices[0].device_type_id):
                # For dual-outlet plugs (mesh_group_id 1 or 2), raw_state is a
                # 2-bit bitmask of active outlets: 1 = outlet 1, 2 = outlet 2, 3 = both.
                raw_state = response[2]
                for device in resolved_devices:
                    if device.mesh_group_id > 0:
                        is_on = device.mesh_group_id == raw_state or raw_state == 3
                    else:
                        is_on = bool(raw_state)
                    device.update_state(is_on, is_online=True)
                    updated_devices[device.unique_id] = device

        if updated_devices and self._update_callback is not None:
            result = self._update_callback(updated_devices)
            if asyncio.iscoroutine(result):
                await result

    async def shut_down(self):
        """Disconnect all active Bluetooth mesh connections."""
        for home_id in list(self._mesh_links.keys()):
            async with self._get_lock(home_id):
                await self._disconnect_home_unlocked(home_id)
        self._unavailable_until.clear()
