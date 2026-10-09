"""
Contains auth information about an authenticated user, and performs generic REST API calls for the user.
"""
import time
from asyncio import TimeoutError
from json import dumps
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession, ClientResponseError

from .const import (GE_CORP_ID, REST_API_BASE_URL, CYNC_ERROR_INVALID_PASSWORD, CYNC_ERROR_INVALID_TWO_FACTOR_CODE,
                    CYNC_ERROR_USER_NOT_FOUND)
from .user import User
from .exceptions import (BadRequestError, TwoFactorRequiredError, AuthFailedError, CyncError, InvalidPasswordError,
                         InvalidTwoFactorCodeError, UnknownAccountError)


async def _read_cync_error(resp: ClientResponse) -> tuple[int | None, str | None]:
    """Return the (code, msg) from a Cync error response body, or (None, None) if the body is not a Cync error."""
    try:
        body = await resp.json(content_type=None)
    except (ValueError, ClientError):
        return None, None

    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return None, None

    code, msg = error.get("code"), error.get("msg")
    if not isinstance(code, int):
        return None, None

    return code, msg if isinstance(msg, str) else None


class Auth:
    def __init__(self, session: ClientSession, user: User = None, username: str = None, password: str = None) -> None:
        """Initialize the auth."""
        self._session = session
        self._user = user
        self._username = username
        self._password = password

    @property
    def user(self):
        return self._user

    @property
    def session(self):
        return self._session

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    async def login(self, two_factor_code: str = None) -> User:
        """
        Attempts to log in with the configured user information.

        If a two factor code is not provided, and the server requests a two factor code, a TwoFactorRequiredError
        will be raised, and at the same time a two factor code will be sent to the user's email.
        This function can then be called again with the two factor code provided to authenticate with the code.
        """
        if two_factor_code is None:
            try:
                user_info = await self._async_auth_user()
                self._user = User(user_info["access_token"], user_info["refresh_token"], user_info["authorize"],
                                  user_info["user_id"], expire_in=user_info["expire_in"])
                return self._user
            except TwoFactorRequiredError as ex:
                two_factor_request = {'corp_id': GE_CORP_ID, 'email': self.username, 'local_lang': "en-us"}

                await self._send_user_request(url=f'{REST_API_BASE_URL}/v2/two_factor/email/verifycode', method="POST",
                                              json=two_factor_request)
                raise TwoFactorRequiredError('Two factor verification required. Code sent to user email.',
                                             error_code=ex.error_code, error_msg=ex.error_msg)
        else:
            user_info = await self._async_auth_user_two_factor(two_factor_code)
            self._user = User(user_info["access_token"], user_info["refresh_token"], user_info["authorize"],
                              user_info["user_id"], expire_in=user_info["expire_in"])
            return self._user

    async def _async_auth_user(self):
        """Attempt to authenticate user without a two factor code."""
        auth_data = {'corp_id': GE_CORP_ID, 'email': self.username, 'password': self.password}

        try:
            auth_response = await self._send_user_request(url=f'{REST_API_BASE_URL}/v2/user_auth', method="POST",
                                                          json=auth_data)
            return auth_response
        except BadRequestError as ex:
            raise TwoFactorRequiredError("Two factor verification required.",
                                         error_code=ex.error_code, error_msg=ex.error_msg) from ex
        except CyncError as ex:
            if ex.error_code == CYNC_ERROR_USER_NOT_FOUND:
                raise UnknownAccountError("No Cync account exists for this email address",
                                          error_code=ex.error_code, error_msg=ex.error_msg) from ex
            raise

    async def _async_auth_user_two_factor(self, two_factor_code: str):
        """Attempt to authenticate user with a two factor code."""
        two_factor_request = {'corp_id': GE_CORP_ID, 'email': self.username, 'password': self.password,
                              'two_factor': two_factor_code, 'resource': 1}

        try:
            auth_response = await self._send_user_request(url=f'{REST_API_BASE_URL}/v2/user_auth/two_factor',
                                                          method="POST", json=two_factor_request)
            return auth_response
        except BadRequestError as ex:
            if ex.error_code == CYNC_ERROR_INVALID_PASSWORD:
                raise InvalidPasswordError("Invalid password",
                                           error_code=ex.error_code, error_msg=ex.error_msg) from ex
            if ex.error_code == CYNC_ERROR_INVALID_TWO_FACTOR_CODE:
                raise InvalidTwoFactorCodeError("Invalid two-factor code",
                                                error_code=ex.error_code, error_msg=ex.error_msg) from ex

            msg = "Two-factor authentication failed"
            if ex.error_code is not None:
                msg = f"{msg} (Cync error {ex.error_code}: {ex.error_msg})"
            raise AuthFailedError(msg, error_code=ex.error_code, error_msg=ex.error_msg) from ex

    async def async_refresh_user_token(self):
        """
        Refresh the user's session token. If the token has already expired, a new login will be required.
        (Likely also requiring a new two factor code to be provided.)
        """
        refresh_request = {'refresh_token': self._user.refresh_token}

        try:
            body = dumps(refresh_request)

            resp = await self.session.request(method="POST", url=f'{REST_API_BASE_URL}/v2/user/token/refresh',
                                              data=body)
            if resp.status != 200:
                raise AuthFailedError('Refresh token failed')

            auth_response = await resp.json()

            self._user.set_new_access_token(auth_response["access_token"], auth_response["refresh_token"],
                                            auth_response["expire_in"])
        except Exception as ex:
            raise AuthFailedError(ex)

    async def _send_user_request(
            self,
            url: str,
            method: str = "GET",
            json: dict[Any, Any] | None = None,
            raise_for_status: bool = True,
    ) -> dict:
        """Send an HTTP request with the provided parameters."""
        headers = {}
        if self.user:
            if self.user.expires_at - time.time() < 3600:
                await self.async_refresh_user_token()
            headers["Access-Token"] = self.user.access_token

        try:
            if json:
                body = dumps(json)

                resp = await self.session.request(method, url, headers=headers, data=body)
            else:
                resp = await self.session.request(method, url, headers=headers)

        except TimeoutError as ex:
            msg = f"Timeout error during query of url {url}: {ex}"
            raise CyncError(msg) from ex
        except Exception as ex:
            msg = f"Unknown error during query of url {url}: {ex}"
            raise CyncError(msg) from ex

        async with resp:
            if resp.status == 400:
                error_code, error_msg = await _read_cync_error(resp)
                raise BadRequestError("Bad Request", error_code=error_code, error_msg=error_msg)

            if resp.status == 401 or resp.status == 403:
                await self.async_refresh_user_token()

                headers["Access-Token"] = self.user.access_token

                if json:
                    body = dumps(json)

                    resp = await self.session.request(method, url, headers=headers, data=body)
                else:
                    resp = await self.session.request(method, url, headers=headers)

            if raise_for_status:
                error_code, error_msg = await _read_cync_error(resp) if resp.status == 404 else (None, None)
                try:
                    resp.raise_for_status()
                except ClientResponseError as ex:
                    msg = (
                        f"HTTP error with status code {resp.status} "
                        f"during query of url {url}: {ex}"
                    )
                    raise CyncError(msg, error_code=error_code, error_msg=error_msg) from ex

            return await resp.json()
