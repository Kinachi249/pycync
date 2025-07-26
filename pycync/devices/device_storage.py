from __future__ import annotations
from typing import Callable, Any, TYPE_CHECKING

from pycync.exceptions import CyncError

if TYPE_CHECKING:
    from pycync.devices.groups import CyncHome

_user_homes: dict[int, UserHomes] = {}

def get_user_homes(user_id: int):
    current_devices = _user_homes.get(user_id, UserHomes([]))
    return current_devices.homes

def set_user_homes(user_id: int, homes: list[CyncHome]):
    current_homes = _user_homes.get(user_id, UserHomes([]))
    current_homes.homes = homes

    _user_homes[user_id] = current_homes

def get_user_device_callback(user_id: int):
    current_homes = _user_homes.get(user_id, UserHomes([]))
    return current_homes.on_data_update

def set_user_device_callback(user_id: int, callback: Callable):
    current_devices = _user_homes.get(user_id, UserHomes([]))
    current_devices.on_data_update = callback

    _user_homes[user_id] = current_devices

def get_associated_home(user_id: int, device_id: int):
    user_homes = _user_homes.get(user_id, UserHomes([])).homes

    found_home = next((home for home in user_homes if home.contains_device_id(device_id)), None)
    if found_home is None:
        raise CyncError(f"Device ID {device_id} not found on user account {user_id}.")
    return found_home

def get_associated_home_devices(user_id: int, device_id: int):
    user_homes = _user_homes.get(user_id, UserHomes([])).homes

    return next((home.get_flattened_device_list() for home in user_homes if home.contains_device_id(device_id)), None)

def get_flattened_devices(user_id: int):
    homes = _user_homes.get(user_id, UserHomes([])).homes
    all_devices = []

    for home in homes:
        all_devices.extend(home.get_flattened_device_list())

    return all_devices

class UserHomes:
    """
    A summary of all homes associated with a user, and an optional callback function
    to call when any of the home's devices are updated.
    """
    def __init__(self, homes: list[CyncHome], on_data_update: Callable[[dict[str, Any]], None] = None):
        self.homes = homes
        self.on_data_update = on_data_update
