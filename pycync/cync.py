from pycync import Auth
from pycync.exceptions import MissingAuthError


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