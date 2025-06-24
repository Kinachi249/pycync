from asyncio import TimeoutError
from json import dumps
from typing import Any

from aiohttp import ClientSession, ClientResponseError

from .const import GE_CORP_ID, REST_API_BASE_URL
from .exceptions import BadRequestError, TwoFactorRequiredError, AuthFailedError
from .user import User


class Auth:
    def __init__(self, session: ClientSession, user_agent: str, username: str, password: str):
        """Initialize the auth."""
        self.user = None
        self.session = session
        self.user_agent = user_agent
        self.username = username
        self.password = password

    async def login_user(self, two_factor_code: str = None) -> User:
        if two_factor_code is None:
            try:
                user_info = await self.async_auth_user()
                self.user = User(user_info)
                return self.user
            except TwoFactorRequiredError as ex:
                two_factor_request = {'corp_id': GE_CORP_ID, 'email': self.username, 'local_lang': "en-us"}

                await self.send_request(url=f'{REST_API_BASE_URL}/v2/two_factor/email/verifycode', method="POST", json=two_factor_request)
                raise TwoFactorRequiredError('Two factor verification required. Code sent to user email.')
            except Exception as ex:
                raise AuthFailedError(ex)
        else:
            try:
                user_info = await self.async_auth_user_two_factor(two_factor_code)
                self.user = User(user_info)
                return self.user
            except Exception as ex:
                raise AuthFailedError(ex)


    async def async_auth_user(self):
        auth_data = {'corp_id': GE_CORP_ID, 'email': self.username, 'password': self.password}

        try:
            auth_response = await self.send_request(url=f'{REST_API_BASE_URL}/v2/user_auth', method="POST", json=auth_data)
            return auth_response
        except BadRequestError as ex:
            raise TwoFactorRequiredError("Two factor verification required.")

    async def async_auth_user_two_factor(self, two_factor_code: str):
        """Docs"""
        two_factor_request = {'corp_id': GE_CORP_ID, 'email': self.username,'password': self.password, 'two_factor': two_factor_code, 'resource': 1}

        try:
            auth_response = await self.send_request(url=f'{REST_API_BASE_URL}/v2/user_auth/two_factor', method="POST", json=two_factor_request)
            return auth_response
        except Exception as ex:
            raise AuthFailedError(ex)

    async def send_request(
        self,
        url: str,
        method: str = "GET",
        extra_params: dict[str, Any] | None = None,
        data: bytes | None = None,
        json: dict[Any, Any] | None = None,
        raise_for_status: bool = True,
    ) -> dict:
        """some stuff"""
        params = {}
        if extra_params:
            params.update(extra_params)

        kwargs: dict[str, Any] = {
            "params": params,
        }
        headers = {"User-Agent": self.user_agent}

        try:
            try:
                body = dumps(json)

                resp = await self.session.request(
                    method, url, headers=headers, data=body, **kwargs
                )
            except Exception:
                raise Exception(f"Generic Exception on Request")
                # TODO implement
                # self._token = await self.async_refresh_tokens()
                # url, headers, data = self._oauth_client.add_token(
                #     url,
                #     http_method=method,
                #     body=data,
                #     headers=headers,
                # )
                # resp = await self._session.request(
                #     method, url, headers=headers, data=data, **kwargs
                # )

        except TimeoutError as ex:
            msg = f"Timeout error during query of url {url}: {ex}"
            raise Exception(msg) from ex
        except Exception as ex:
            msg = f"Unknown error during query of url {url}: {ex}"
            raise Exception(msg) from ex

        async with resp:
            if resp.status == 400:
                raise BadRequestError("Bad Request")

            # if resp.status == 401:
                # Check whether there's an issue with the token grant
                # self._token = await self.async_refresh_tokens()

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
