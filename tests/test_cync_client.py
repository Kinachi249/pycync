import json
import time
from typing import List

import pytest
from pycync.devices import device_storage
from unittest.mock import patch

from pycync import User, Cync, CyncDevice, CyncHome, CyncRoom, CyncGroup

MOCKED_USER = User(
    "test_token",
    "test_refresh_token",
    "test_authorize_string",
    123456789,
    expires_at=(time.time() * 1000) + 3600000,
)
MOCKED_EMAIL = "test@testuser.com"


@pytest.fixture(autouse=True)
def auth_client():
    """Mock a pycync.Auth client."""
    with patch(
        "pycync.cync.Auth", autospec=True
    ) as sc_class_mock:
        client_mock = sc_class_mock.return_value
        client_mock.user = MOCKED_USER
        client_mock.username = MOCKED_EMAIL
        yield client_mock

@pytest.fixture(autouse=True)
def command_client():
    """Mock a CommandClient."""
    with patch(
        "pycync.cync.CommandClient", autospec=True
    ) as command_client_mock:
        command_client_mock.return_value = command_client_mock
        yield command_client_mock

def home_info_responses(*args):
    if args[0].endswith("/subscribe/devices"):
        with open("fixtures/device_api_response.json") as f:
            return json.load(f)
    elif args[0].endswith("/property"):
        with open("fixtures/property_api_response.json") as f:
            return json.load(f)
    else:
        return None

@pytest.mark.asyncio
async def test_refresh_home_info(auth_client, command_client):
    auth_client._send_user_request.side_effect = home_info_responses

    cync: Cync = await Cync.create(auth_client)

    await cync.refresh_home_info()
    homes: List[CyncHome] = device_storage.get_user_homes(MOCKED_USER.user_id)

    assert len(homes) == 1

    rooms: List[CyncRoom] = homes[0].rooms
    assert len(rooms) == 4

    office: CyncRoom = next(room for room in rooms if room.name == "Office")
    assert office is not None
    assert len(office.devices) == 0
    assert len(office.groups) == 1

    office_lamp: CyncGroup = office.groups[0]
    assert office_lamp is not None
    assert office_lamp.name == "Office Lamp"
    assert len(office_lamp.devices) == 0

    bedroom: CyncRoom = next(room for room in rooms if room.name == "Bedroom")
    assert bedroom is not None
    assert len(bedroom.devices) == 1
    device: CyncDevice = bedroom.devices[0]
    assert device.name == "Bedroom Lamp"
    assert device.parent_home_id == 9000
    assert device.device_id == 6874
    assert device.isolated_mesh_id == 2
