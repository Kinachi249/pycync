from pycync import Auth
from pycync.exceptions import MissingAuthError
from pycync.const import REST_API_BASE_URL


class Cync:
    """Docs."""
    def __init__(self, auth: Auth):
        """Initialize the Cync object."""
        if not auth.user:
            raise MissingAuthError("No logged in user exists on auth object.")
        self.auth = auth

    def get_logged_in_user(self):
        """Get logged in user."""

        return self.auth.user

    async def get_device_list(self):
        """Get list of devices."""
        return await self.auth.send_request(f"{REST_API_BASE_URL}/v2/user/{self.auth.user.user_id}/subscribe/devices")