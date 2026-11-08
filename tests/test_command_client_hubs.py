import pytest
from unittest.mock import AsyncMock

from pycync import CyncHome, CyncDevice, CyncRoom
from pycync.devices import device_storage
from pycync.devices.device_types import DeviceType
from pycync.tcp.command_client import CommandClient
from pycync.user import User

# A user of its own: device_storage is module-global, and other test files expect TEST_USER_ID to start empty.
HUBS_USER_ID = 765432
HOME_ID = 4567
PLUG_TYPE = 172  # Wi-Fi plug, can act as a Wi-Fi proxy into the mesh
BULB_TYPE = 17   # Bluetooth-only bulb, cannot


def _device(mesh_id: int, name: str, type_id: int, wifi_connected: bool) -> CyncDevice:
    return CyncDevice(True, wifi_connected, mesh_id, mesh_id, HOME_ID, name, type_id, DeviceType.LIGHT,
                      f"{mesh_id:012X}", "ID1", "Code")


@pytest.fixture
def devices():
    plug_1 = _device(15, "Plug 1", PLUG_TYPE, True)
    plug_2 = _device(16, "Plug 2", PLUG_TYPE, True)
    plug_offline = _device(17, "Plug 3", PLUG_TYPE, False)
    bulb = _device(7, "Bulb", BULB_TYPE, False)
    home = CyncHome("Home", HOME_ID, [CyncRoom("Room", 1, HOME_ID, [], [plug_1, plug_2, plug_offline, bulb])], [])
    device_storage.set_user_homes(HUBS_USER_ID, [home])
    return plug_1, plug_2, plug_offline, bulb


@pytest.fixture
def client():
    client = CommandClient(User("access", "refresh", "authorize", HUBS_USER_ID, 0))
    client._device_statuses_updated = True
    client._tcp_manager = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_command_is_sent_through_every_connected_hub(client, devices):
    plug_1, plug_2, plug_offline, bulb = devices

    await client.set_power_state(bulb, True)

    hubs = [call.args[0] for call in client._tcp_manager.set_power_state.await_args_list]
    assert hubs == [plug_1, plug_2]
    assert all(call.args[1:] == (bulb.mesh_reference_id, bulb.mesh_group_id, True)
               for call in client._tcp_manager.set_power_state.await_args_list)


@pytest.mark.asyncio
async def test_brightness_is_sent_through_every_connected_hub(client, devices):
    plug_1, plug_2, plug_offline, bulb = devices

    await client.set_brightness(bulb, 40)

    hubs = [call.args[0] for call in client._tcp_manager.set_brightness.await_args_list]
    assert hubs == [plug_1, plug_2]
