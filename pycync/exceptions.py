class CyncError(Exception):
    """Cync error."""

class TwoFactorRequiredError(CyncError):
    """Two-factor required."""

class AuthFailedError(CyncError):
    """Auth failed."""

class NoHubConnectedError(CyncError):
    """No hub device is connected to Wi-Fi."""

class MissingAuthError(Exception):
    """Missing auth error."""

class BadRequestError(Exception):
    """For HTTP 400 Responses."""

class UnsupportedCapabilityError(Exception):
    """When a property that the device doesn't support is attempted to be accessed."""