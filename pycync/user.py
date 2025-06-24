import time

class User:
    """Docs."""

    def __init__(self, raw_user_info: dict):
        """Initialize the User object."""
        self.raw_user_info = raw_user_info
        self.expires_at = time.time() + raw_user_info.get('expire_in')

    @property
    def access_token(self) -> str:
        """Return the user's access token."""
        return self.raw_user_info["access_token"]

    @property
    def refresh_token(self) -> str:
        """Return the ID of the light."""
        return self.raw_user_info["refresh_token"]

    @property
    def expire_in(self) -> int:
        """Return the ID of the light."""
        return self.raw_user_info["expire_in"]

    @property
    def authorize(self) -> str:
        """Return the ID of the light."""
        return self.raw_user_info["authorize"]

    @property
    def user_id(self) -> int:
        """Return the ID of the light."""
        return self.raw_user_info["user_id"]

    def __str__(self):
        """Return a string representation of the user."""
        return f"User(ID: {self.user_id}, authorize string: {self.authorize})"