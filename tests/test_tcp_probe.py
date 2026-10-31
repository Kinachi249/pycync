"""Probing over Wi-Fi skips Bluetooth-only devices: they have no radio to answer, and their stand-in device ID (the
mesh deviceID, e.g. 1234567890004) does not fit the probe packet's 4-byte device ID field, so building a probe for it
raises OverflowError. That is the likely cause of the reconnect loop reported in issue #17."""
import asyncio
from unittest.mock import AsyncMock

from pycync import CyncLight
from pycync.devices.device_types import DeviceType
from pycync.devices.devices import CyncPlug
from pycync.tcp import packet_builder
from pycync.tcp.tcp_manager import TcpManager


def test_probe_skips_bluetooth_only_devices():
    hub = CyncPlug(True, True, 2345, 15, 5432, "Hub Plug", 172, DeviceType.PLUG, "223456ABCDEF", "ID1", "Code")
    bulb = CyncLight(False, False, 1234567890004, 4, 5432, "Bluetooth Bulb", 17, DeviceType.LIGHT, None, None, None)
    bulb.bluetooth_only = True

    manager = TcpManager.__new__(TcpManager)  # skip __init__, which opens a connection
    manager._send_request = AsyncMock()

    asyncio.run(manager.probe_devices([hub, bulb]))

    # Exactly one probe, for the hub. Packets carry a running counter, so compare the device ID bytes, not the packet.
    manager._send_request.assert_awaited_once()
    assert (2345).to_bytes(4, "big") in manager._send_request.await_args.args[0]


def test_bluetooth_only_stand_in_id_cannot_be_probed():
    # Documents why the skip matters: the stand-in ID overflows the 4-byte field.
    try:
        packet_builder.build_probe_request_packet(1234567890004)
    except OverflowError:
        return
    raise AssertionError("expected OverflowError for a mesh deviceID in the 4-byte probe field")
