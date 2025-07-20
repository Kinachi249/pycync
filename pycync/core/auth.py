from asyncio import TimeoutError
from json import dumps
from typing import Any
import time

from aiohttp import ClientSession, ClientResponseError

from pycync import CyncDevice
from pycync.const import GE_CORP_ID, REST_API_BASE_URL
from pycync.exceptions import BadRequestError, TwoFactorRequiredError, AuthFailedError


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


class Auth:
    def __init__(self, session: ClientSession, user_agent: str, user: User = None, username: str = None, password: str = None) -> None:
        """Initialize the auth."""
        self._session = session
        self._user_agent = user_agent
        self._user = user
        self._username = username
        self._password = password
        self._device_credentials = {}

    @property
    def user(self):
        return self._user

    @property
    def session(self):
        return self._session

    @property
    def user_agent(self):
        return self._user_agent

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    async def login_user(self, two_factor_code: str = None) -> User:
        if two_factor_code is None:
            try:
                user_info = await self.async_auth_user()
                self._user = User(user_info["access_token"], user_info["refresh_token"], user_info["authorize"], user_info["user_id"], expire_in=user_info["expire_in"])
                return self._user
            except TwoFactorRequiredError as ex:
                two_factor_request = {'corp_id': GE_CORP_ID, 'email': self.username, 'local_lang': "en-us"}

                await self.send_user_request(url=f'{REST_API_BASE_URL}/v2/two_factor/email/verifycode', method="POST", json=two_factor_request)
                raise TwoFactorRequiredError('Two factor verification required. Code sent to user email.')
            except Exception as ex:
                raise AuthFailedError(ex)
        else:
            try:
                user_info = await self.async_auth_user_two_factor(two_factor_code)
                self._user = User(user_info["access_token"], user_info["refresh_token"], user_info["authorize"], user_info["user_id"], expire_in=user_info["expire_in"])
                return self._user
            except Exception as ex:
                raise AuthFailedError(ex)

    async def async_auth_user(self):
        auth_data = {'corp_id': GE_CORP_ID, 'email': self.username, 'password': self.password}

        try:
            auth_response = await self.send_user_request(url=f'{REST_API_BASE_URL}/v2/user_auth', method="POST", json=auth_data)
            return auth_response
        except BadRequestError as ex:
            raise TwoFactorRequiredError("Two factor verification required.")

    async def async_auth_user_two_factor(self, two_factor_code: str):
        """Docs"""
        two_factor_request = {'corp_id': GE_CORP_ID, 'email': self.username,'password': self.password, 'two_factor': two_factor_code, 'resource': 1}

        try:
            auth_response = await self.send_user_request(url=f'{REST_API_BASE_URL}/v2/user_auth/two_factor', method="POST", json=two_factor_request)
            return auth_response
        except Exception as ex:
            raise AuthFailedError(ex)

    async def async_refresh_user_token(self):
        """Docs"""
        refresh_request = {'refresh_token': self._user.refresh_token}

        try:
            body = dumps(refresh_request)

            resp = await self.session.request(method="POST", url=f'{REST_API_BASE_URL}/v2/user/token/refresh', data=body)
            if resp.status != 200:
                raise AuthFailedError('Refresh token failed')

            auth_response = await resp.json()

            self._user.access_token = auth_response["access_token"]
            self._user.refresh_token = auth_response["refresh_token"]
        except Exception as ex:
            raise AuthFailedError(ex)

    async def send_user_request(
        self,
        url: str,
        method: str = "GET",
        json: dict[Any, Any] | None = None,
        raise_for_status: bool = True,
    ) -> dict:
        """some stuff"""
        headers = {"User-Agent": self.user_agent}
        if self.user:
            headers["Access-Token"] = self.user.access_token

        try:
            try:
                if json:
                    body = dumps(json)

                    resp = await self.session.request(method, url, headers=headers, data=body)
                else:
                    resp = await self.session.request(method, url, headers=headers)
            except Exception:
                await self.async_refresh_user_token()
                headers["Access-Token"] = self.user.access_token

                if json:
                    body = dumps(json)

                    resp = await self.session.request(method, url, headers=headers, data=body)
                else:
                    resp = await self.session.request(method, url, headers=headers)

        except TimeoutError as ex:
            msg = f"Timeout error during query of url {url}: {ex}"
            raise Exception(msg) from ex
        except Exception as ex:
            msg = f"Unknown error during query of url {url}: {ex}"
            raise Exception(msg) from ex

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
                    raise Exception(msg) from ex

            return await resp.json()
