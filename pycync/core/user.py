import time
from typing import Callable, Any

from pycync import CyncDevice


class User:
    """Docs."""

    def __init__(self, access_token: str, refresh_token: str, authorize: str, user_id: int, expire_in: int = None, expires_at: float = None):
        """Initialize the User object."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expire_in = expire_in
        self._authorize = authorize
        self._user_id = user_id
        self._expires_at = time.time() + expire_in if not expires_at else expires_at

    @property
    def access_token(self) -> str:
        """Return the user's access token."""
        return self._access_token

    @property
    def refresh_token(self) -> str:
        """Return the ID of the light."""
        return self._refresh_token

    @property
    def expire_in(self) -> int:
        """Return the ID of the light."""
        return self._expire_in

    @property
    def expires_at(self) -> float:
        """Return the ID of the light."""
        return self._expires_at

    @property
    def authorize(self) -> str:
        """Return the ID of the light."""
        return self._authorize

    @property
    def user_id(self) -> int:
        """Return the ID of the light."""
        return self._user_id

class UserDevices:
    def __init__(self, devices: list[CyncDevice], on_data_update: Callable[[dict[str, Any]], None] = None):
        self.devices = devices
        self.on_data_update = on_data_update