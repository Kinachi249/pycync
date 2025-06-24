from aiohttp import ClientResponseError

class CyncError(Exception):
    """Cync error."""

class TwoFactorRequiredError(CyncError):
    """Two-factor required."""

class AuthFailedError(CyncError):
    """Auth failed."""

class MissingAuthError(Exception):
    """Missing auth error."""

class BadRequestError(Exception):
    """For HTTP 400 Responses."""