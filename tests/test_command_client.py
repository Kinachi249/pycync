import pytest

from pycync import CyncHome, CyncDevice, CyncRoom
from pycync.devices import device_storage
from pycync.devices.device_types import DeviceType
from pycync.tcp.command_client import CommandClient
from pycync.tcp.packet import MessageType, ParsedMessage, PipeCommandCode
from pycync.user import User

# A user of its own: device_storage is module-global, and other test files expect TEST_USER_ID to start empty.
COMMAND_CLIENT_USER_ID = 654321


def _device(mesh_id: int, home_id: int, name: str) -> CyncDevice:
    return CyncDevice(True, True, mesh_id, mesh_id, home_id, name, 224, DeviceType.LIGHT, f"{mesh_id:012X}", "ID1", "Code")


@pytest.fixture
def homes():
    home_1_device_1 = _device(12, 1234, "Home 1 Device 1")
    home_1_device_2 = _device(23, 1234, "Home 1 Device 2")
    home_2_device_1 = _device(34, 2345, "Home 2 Device 1")
    home_1 = CyncHome("Home 1", 1234, [CyncRoom("Room 1", 1, 1234, [], [home_1_device_1, home_1_device_2])], [])
    home_2 = CyncHome("Home 2", 2345, [CyncRoom("Room 1", 2, 2345, [], [home_2_device_1])], [])
    device_storage.set_user_homes(COMMAND_CLIENT_USER_ID, [home_1, home_2])
    return home_1_device_1, home_1_device_2, home_2_device_1


@pytest.fixture
def client():
    return CommandClient(User("access", "refresh", "authorize", COMMAND_CLIENT_USER_ID, 0))


def _status_reply(devices: list[CyncDevice]) -> ParsedMessage:
    return ParsedMessage(MessageType.PIPE.value, True, 12, {device.unique_id: device for device in devices}, 3,
                         PipeCommandCode.QUERY_DEVICE_STATUS_PAGES.value)


@pytest.mark.asyncio
async def test_empty_status_reply_keeps_devices_online(client, homes):
    await client.on_message_received(_status_reply([]))

    assert all(device.is_online for device in homes)


@pytest.mark.asyncio
async def test_device_missing_from_page_is_not_marked_offline(client, homes):
    home_1_device_1, home_1_device_2, home_2_device_1 = homes

    await client.on_message_received(_status_reply([home_1_device_1]))

    # e.g. the 16th device on an account: a page holds at most 15.
    assert home_1_device_2.is_online
    assert home_2_device_1.is_online


@pytest.mark.asyncio
async def test_status_reply_is_forwarded_to_listener(client, homes):
    home_1_device_1, _, _ = homes
    received = []
    device_storage.set_user_device_callback(COMMAND_CLIENT_USER_ID, received.append)

    await client.on_message_received(_status_reply([home_1_device_1]))

    assert received == [{home_1_device_1.unique_id: home_1_device_1}]
