from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from pycync import User
from pycync.tcp.command_client import CommandClient
from pycync.tcp.packet import MessageType, ParsedMessage, PipeCommandCode

MOCKED_USER = User("test_token", "test_refresh_token", "test_authorize_string", 987654321, expire_in=3600)

DEVICES = [SimpleNamespace(unique_id=f"home-{i}", is_online=False) for i in range(28)]


@pytest.fixture(autouse=True)
def flattened_devices():
    with patch("pycync.devices.device_storage.get_flattened_devices", return_value=DEVICES):
        for device in DEVICES:
            device.is_online = False
        yield


@pytest.fixture
def command_client():
    client = CommandClient(MOCKED_USER)
    client._tcp_manager = AsyncMock()
    return client


def status_page(devices):
    return ParsedMessage(MessageType.PIPE.value, True, 1, {device.unique_id: device for device in devices}, 3,
                         PipeCommandCode.QUERY_DEVICE_STATUS_PAGES.value)


def online_ids():
    return {device.unique_id for device in DEVICES if device.is_online}


@pytest.mark.asyncio
async def test_status_pages_from_one_poll_are_combined(command_client):
    await command_client.update_mesh_devices()
    await command_client.on_message_received(status_page(DEVICES[:25]))
    await command_client.on_message_received(status_page(DEVICES[25:]))

    assert online_ids() == {device.unique_id for device in DEVICES}


@pytest.mark.asyncio
async def test_empty_first_page_keeps_devices_from_last_poll_online(command_client):
    await command_client.update_mesh_devices()
    await command_client.on_message_received(status_page(DEVICES))

    await command_client.update_mesh_devices()
    await command_client.on_message_received(status_page([]))

    assert online_ids() == {device.unique_id for device in DEVICES}


@pytest.mark.asyncio
async def test_device_missing_from_two_polls_goes_offline(command_client):
    await command_client.update_mesh_devices()
    await command_client.on_message_received(status_page(DEVICES))

    for _ in range(2):
        await command_client.update_mesh_devices()
        await command_client.on_message_received(status_page(DEVICES[1:]))

    assert DEVICES[0].unique_id not in online_ids()
    assert len(online_ids()) == 27
