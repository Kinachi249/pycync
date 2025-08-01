"""
Contains auth information about an authenticated user, and performs generic REST API calls for the user.
"""
import time
from asyncio import TimeoutError
from json import dumps
from typing import Any

from aiohttp import ClientSession, ClientResponseError

from .const import GE_CORP_ID, REST_API_BASE_URL
from .user import User
from .exceptions import BadRequestError, TwoFactorRequiredError, AuthFailedError, CyncError


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
            except TwoFactorRequiredError:
                two_factor_request = {'corp_id': GE_CORP_ID, 'email': self.username, 'local_lang': "en-us"}

                await self._send_user_request(url=f'{REST_API_BASE_URL}/v2/two_factor/email/verifycode', method="POST",
                                              json=two_factor_request)
                raise TwoFactorRequiredError('Two factor verification required. Code sent to user email.')
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
        except BadRequestError:
            raise TwoFactorRequiredError("Two factor verification required.")

    async def _async_auth_user_two_factor(self, two_factor_code: str):
        """Attempt to authenticate user with a two factor code."""
        two_factor_request = {'corp_id': GE_CORP_ID, 'email': self.username, 'password': self.password,
                              'two_factor': two_factor_code, 'resource': 1}

        try:
            auth_response = await self._send_user_request(url=f'{REST_API_BASE_URL}/v2/user_auth/two_factor',
                                                          method="POST", json=two_factor_request)
            return auth_response
        except BadRequestError as ex:
            raise AuthFailedError("Invalid two-factor code") from ex

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
                raise BadRequestError("Bad Request")

            if resp.status == 401 or resp.status == 403:
                await self.async_refresh_user_token()

                headers["Access-Token"] = self.user.access_token

                if json:
                    body = dumps(json)

                    resp = await self.session.request(method, url, headers=headers, data=body)
                else:
                    resp = await self.session.request(method, url, headers=headers)

            if raise_for_status:
                try:
                    resp.raise_for_status()
                except ClientResponseError as ex:
                    msg = (
                        f"HTTP error with status code {resp.status} "
                        f"during query of url {url}: {ex}"
                    )
                    raise CyncError(msg) from ex

            return await resp.json()
