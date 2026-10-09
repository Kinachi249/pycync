class CyncError(Exception):
    """Cync error."""

    def __init__(self, *args, error_code: int | None = None, error_msg: str | None = None):
        super().__init__(*args)
        self.error_code = error_code
        self.error_msg = error_msg

class TwoFactorRequiredError(CyncError):
    """Two-factor required."""

class AuthFailedError(CyncError):
    """Auth failed."""

class InvalidPasswordError(AuthFailedError):
    """The Cync account password was rejected."""

class InvalidTwoFactorCodeError(AuthFailedError):
    """The two-factor code was rejected."""

class UnknownAccountError(AuthFailedError):
    """No Cync account exists for the email address."""

class NoHubConnectedError(CyncError):
    """No hub device is connected to Wi-Fi."""

class MissingAuthError(Exception):
    """Missing auth error."""

class BadRequestError(Exception):
    """For HTTP 400 Responses."""

    def __init__(self, *args, error_code: int | None = None, error_msg: str | None = None):
        super().__init__(*args)
        self.error_code = error_code
        self.error_msg = error_msg

class UnsupportedCapabilityError(Exception):
    """When a property that the device doesn't support is attempted to be accessed."""