import pytest

from pycync import CyncHome, CyncDevice, CyncGroup, CyncRoom
from pycync.devices import device_storage
from pycync.devices.device_types import DeviceType
from pycync.exceptions import CyncError
from tests import TEST_USER_ID


home_1 = CyncHome("Home 1", 1234, [], [])
home_2 = CyncHome("Home 2", 2345, [], [])

home_1_room_1_group_1_device_1 = CyncDevice(True, True, 12, 2, 1234, "Device 1", 224, DeviceType.LIGHT, "123456ABCDEF", "ID1", "Code")
home_1_room_1_group_1_device_2 = CyncDevice(True, True, 23, 3, 1234, "Device 2", 224, DeviceType.LIGHT, "223456ABCDEF", "ID1", "Code")
home_1_room_1_group_1 = CyncGroup("Group 1", 1, 1234, [home_1_room_1_group_1_device_1, home_1_room_1_group_1_device_2])

home_1_room_1_device_1 = CyncDevice(True, True, 34, 4, 1234, "Device 3", 224, DeviceType.LIGHT, "323456ABCDEF", "ID1", "Code")
home_1_room_1 = CyncRoom("Room 1", 2, 1234, [home_1_room_1_group_1], [home_1_room_1_device_1])

home_1_room_2_device_1 = CyncDevice(True, True, 45, 5, 1234, "Device 4", 224, DeviceType.LIGHT, "423456ABCDEF", "ID1", "Code")
home_1_room_2 = CyncRoom("Room 2", 3, 1234, [], [home_1_room_2_device_1], None)

home_2_room_1_device_1 = CyncDevice(True, True, 56, 6, 2345, "Device 5", 224, DeviceType.LIGHT, "523456ABCDEF", "ID1", "Code")
home_2_room_1_device_2 = CyncDevice(True, True, 67, 7, 2345, "Device 6", 224, DeviceType.LIGHT, "623456ABCDEF", "ID1", "Code")
home_2_room_1 = CyncRoom("Room 1", 4, 2345, [], [home_2_room_1_device_1, home_2_room_1_device_2], None)

home_2_device_1 = CyncDevice(True, True, 78, 8, 2345, "Device 7", 224, DeviceType.LIGHT, "723456ABCDEF", "ID1", "Code")
home_2_device_2 = CyncDevice(True, True, 89, 9, 2345, "Device 8", 224, DeviceType.LIGHT, "823456ABCDEF", "ID1", "Code")

home_1.rooms = [home_1_room_1, home_1_room_2]
home_2.rooms = [home_2_room_1]
home_2.global_devices = [home_2_device_1, home_2_device_2]

def test_get_user_homes_no_entries():
    homes: list[CyncHome] = device_storage.get_user_homes(TEST_USER_ID)

    assert len(homes) == 0

def test_set_and_get_user_devices():
    device_storage.set_user_homes(TEST_USER_ID, [home_1, home_2])

    all_devices = device_storage.get_flattened_devices(TEST_USER_ID)

    expected_devices = [
        home_1_room_1_group_1_device_1,
        home_1_room_1_group_1_device_2,
        home_1_room_1_device_1,
        home_1_room_2_device_1,
        home_2_room_1_device_1,
        home_2_room_1_device_2,
        home_2_device_1,
        home_2_device_2
    ]

    result_difference = set(all_devices).difference(set(expected_devices))
    assert not result_difference

def test_set_and_get_user_homes():
    device_storage.set_user_homes(TEST_USER_ID, [home_1, home_2])

    all_homes = device_storage.get_user_homes(TEST_USER_ID)

    expected_homes = [
        home_1,
        home_2
    ]

    result_difference = set(all_homes).difference(set(expected_homes))
    assert not result_difference

def test_get_callback_not_set():
    callback = device_storage.get_user_device_callback(TEST_USER_ID)

    assert callback is None

def test_set_and_get_callback():
    def my_callback():
        return 42

    device_storage.set_user_device_callback(TEST_USER_ID, my_callback)

    callback = device_storage.get_user_device_callback(TEST_USER_ID)

    assert callback == my_callback
    assert callback() == 42

def test_get_associated_home():
    device_storage.set_user_homes(TEST_USER_ID, [home_1, home_2])

    home_1_test_1 = device_storage.get_associated_home(TEST_USER_ID, home_1_room_1_group_1_device_1.device_id)
    home_1_test_2 = device_storage.get_associated_home(TEST_USER_ID, home_1_room_1_device_1.device_id)
    home_1_test_3 = device_storage.get_associated_home(TEST_USER_ID, home_1_room_2_device_1.device_id)
    home_2_test_1 = device_storage.get_associated_home(TEST_USER_ID, home_2_room_1_device_1.device_id)
    home_2_test_2 = device_storage.get_associated_home(TEST_USER_ID, home_2_device_1.device_id)

    assert home_1_test_1 == home_1
    assert home_1_test_2 == home_1
    assert home_1_test_3 == home_1
    assert home_2_test_1 == home_2
    assert home_2_test_2 == home_2

def test_get_associated_home_device_not_found():
    device_storage.set_user_homes(TEST_USER_ID, [home_1, home_2])

    with pytest.raises(CyncError,
                       match=f'Device ID 9876 not found on user account {TEST_USER_ID}.'):
        device_storage.get_associated_home(TEST_USER_ID, 9876)

def test_get_devices_in_associated_home():
    device_storage.set_user_homes(TEST_USER_ID, [home_1, home_2])

    home_1_devices = [
        home_1_room_1_group_1_device_1,
        home_1_room_1_group_1_device_2,
        home_1_room_1_device_1,
        home_1_room_2_device_1
    ]

    home_2_devices = [
        home_2_room_1_device_1,
        home_2_room_1_device_2,
        home_2_device_1,
        home_2_device_2
    ]

    home_1_test_1 = device_storage.get_associated_home_devices(TEST_USER_ID, home_1_room_1_group_1_device_1.device_id)
    home_1_test_2 = device_storage.get_associated_home_devices(TEST_USER_ID, home_1_room_1_device_1.device_id)
    home_1_test_3 = device_storage.get_associated_home_devices(TEST_USER_ID, home_1_room_2_device_1.device_id)
    home_2_test_1 = device_storage.get_associated_home_devices(TEST_USER_ID, home_2_room_1_device_1.device_id)
    home_2_test_2 = device_storage.get_associated_home_devices(TEST_USER_ID, home_2_device_1.device_id)

    assert not set(home_1_test_1).difference(set(home_1_devices))
    assert not set(home_1_test_2).difference(set(home_1_devices))
    assert not set(home_1_test_3).difference(set(home_1_devices))
    assert not set(home_2_test_1).difference(set(home_2_devices))
    assert not set(home_2_test_2).difference(set(home_2_devices))