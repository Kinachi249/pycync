import time


class User:
    """A Cync user account and their auth credentials."""

    def __init__(self, access_token: str, refresh_token: str, authorize: str, user_id: int, expire_in: int = None,
                 expires_at: float = None):
        """Initialize the User object."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._authorize = authorize
        self._user_id = user_id
        self._expires_at = time.time() + expire_in if not expires_at else expires_at

    @property
    def access_token(self) -> str:
        """Return the user's access token."""
        return self._access_token

    @property
    def refresh_token(self) -> str:
        """Return the user's refresh token."""
        return self._refresh_token

    @property
    def expires_at(self) -> float:
        """Return the epoch millis at which the token expires."""
        return self._expires_at

    @property
    def authorize(self) -> str:
        """Return the "authorize" string used when authenticating the TCP connection."""
        return self._authorize

    @property
    def user_id(self) -> int:
        """Return the ID of the user."""
        return self._user_id

    def set_new_access_token(self, access_token: str, refresh_token: str, expire_in: float):
        """Set the new access token."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at = time.time() + expire_in
