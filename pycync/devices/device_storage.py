from __future__ import annotations
from typing import Callable, TYPE_CHECKING

from pycync.exceptions import CyncError

if TYPE_CHECKING:
    from pycync.devices.groups import CyncHome

_user_homes: dict[int, UserHomes] = {}


def get_user_homes(user_id: int):
    """Fetch a list of all configured homes for the user."""

    current_homes = _user_homes.get(user_id, UserHomes([]))
    return current_homes.homes


def get_home_by_id(user_id: int, home_id: int):
    """Fetch a home by the user and home ID."""

    user_homes = _user_homes.get(user_id, UserHomes([])).homes

    found_home = next((home for home in user_homes if home.home_id == home_id), None)
    if found_home is None:
        raise CyncError(f"Home ID {home_id} not found on user account {user_id}.")
    return found_home


def set_user_homes(user_id: int, homes: list[CyncHome]):
    """Set a list of configured homes for the user."""

    current_homes = _user_homes.get(user_id, UserHomes([]))
    current_homes.homes = homes

    _user_homes[user_id] = current_homes


def get_user_device_callback(user_id: int):
    """Get the configured device update callback function for the user."""

    current_homes = _user_homes.get(user_id, UserHomes([]))
    return current_homes.on_data_update


def set_user_device_callback(user_id: int, callback: Callable):
    """Set the configured device update callback function for the user."""

    current_homes = _user_homes.get(user_id, UserHomes([]))
    current_homes.on_data_update = callback

    _user_homes[user_id] = current_homes


def get_associated_home(user_id: int, device_id: int):
    """Get the home that the provided device id belongs to."""

    user_homes = _user_homes.get(user_id, UserHomes([])).homes

    found_home = next((home for home in user_homes if home.contains_device_id(device_id)), None)
    if found_home is None:
        raise CyncError(f"Device ID {device_id} not found on user account {user_id}.")
    return found_home


def get_associated_home_devices(user_id: int, device_id: int):
    """Given a device ID, returns a list of all devices that exist in the same home that the device ID belongs to."""

    home_for_device = get_associated_home(user_id, device_id)
    return home_for_device.get_flattened_device_list()


def get_flattened_devices(user_id: int):
    """Returns a list of all devices that have been configured for the user, across all homes."""

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

    def __init__(self, homes: list[CyncHome], on_data_update: Callable = None):
        self.homes = homes
        self.on_data_update = on_data_update
