from asyncio import TimeoutError
from json import dumps, loads
from typing import Any

from aiohttp import ClientSession

from .const import GE_CORP_ID, REST_API_BASE_URL
from .cync import Cync


class Auth:
    def __init__(self, session: ClientSession, user_agent: str, username: str, password: str):
        """Initialize the auth."""
        self.session = session
        self.user_agent = user_agent
        self.username = username
        self.password = password

    async def get_cync_instance(self):
        try:
            await self.async_get_token()
        except Exception as ex:
            raise Exception(str(ex))
        else:
            return Cync()


    async def async_get_token(self):
        auth_data = {'corp_id': GE_CORP_ID, 'email': self.username, 'password': self.password}

        try:
            auth_resp = await self.send_request(url=f'{REST_API_BASE_URL}/v2/user_auth', method="POST", json=auth_data)
        except Exception as ex:
            raise Exception(str(ex))

    async def verify_two_factor_code(self, two_factor_code: str):
        """Docs"""

    class Response:
        """Class for returning responses."""

        def __init__(self, content: bytes, status_code: int) -> None:
            """Initialise thhe repsonse class."""
            self.content = content
            self.status_code = status_code

        @property
        def text(self) -> str:
            """Response as text."""
            return self.content.decode()

        def json(self) -> Any:
            """Response as loaded json."""
            return loads(self.text)

    async def send_request(
        self,
        url: str,
        method: str = "GET",
        extra_params: dict[str, Any] | None = None,
        data: bytes | None = None,
        json: dict[Any, Any] | None = None,
        raise_for_status: bool = True,
    ) -> Response:
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
            # if resp.status == 401:
                # Check whether there's an issue with the token grant
                # self._token = await self.async_refresh_tokens()

            if raise_for_status:
                try:
                    resp.raise_for_status()
                except Exception as ex:
                    msg = (
                        f"HTTP error with status code {resp.status} "
                        f"during query of url {url}: {ex}"
                    )
                    raise Exception(msg) from ex

            response_data = await resp.read()
        return Auth.Response(response_data, resp.status)
