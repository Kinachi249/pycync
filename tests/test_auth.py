import json
from unittest.mock import MagicMock

import pytest
from aiohttp import ClientResponseError

from pycync import Auth, User
from pycync.exceptions import (AuthFailedError, BadRequestError, CyncError, InvalidPasswordError,
                               InvalidTwoFactorCodeError, TwoFactorRequiredError, UnknownAccountError)

TOKENS = {
    "access_token": "test_access_token",
    "refresh_token": "test_refresh_token",
    "authorize": "test_authorize",
    "user_id": 123456789,
    "expire_in": 604800,
}


def cync_error(code, msg):
    return {"error": {"msg": msg, "code": code}}


class FakeResponse:
    def __init__(self, status, body=None, *, raw=None):
        self.status = status
        self._raw = raw if raw is not None else json.dumps(body or {}).encode()

    async def json(self, content_type="application/json", **kwargs):
        return json.loads(self._raw)

    def raise_for_status(self):
        if self.status >= 400:
            raise ClientResponseError(MagicMock(), (), status=self.status, message="error")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def request(self, method, url, headers=None, data=None, **kwargs):
        self.calls.append({"method": method, "url": url, "data": json.loads(data) if data else None})
        return self.responses.pop(0)


def make_auth(responses):
    session = FakeSession(responses)
    return Auth(session, username="user@example.com", password="pw"), session


@pytest.mark.asyncio
async def test_two_factor_wrong_password_raises_invalid_password_error():
    auth, _ = make_auth([FakeResponse(400, cync_error(4001007, "password error"))])

    with pytest.raises(InvalidPasswordError) as exc_info:
        await auth.login("123456")

    assert isinstance(exc_info.value, AuthFailedError)
    assert exc_info.value.error_code == 4001007


@pytest.mark.asyncio
async def test_two_factor_error_without_msg_still_maps_code():
    auth, _ = make_auth([FakeResponse(400, {"error": {"code": 4001007}})])

    with pytest.raises(InvalidPasswordError) as exc_info:
        await auth.login("123456")

    assert exc_info.value.error_code == 4001007
    assert exc_info.value.error_msg is None


@pytest.mark.asyncio
async def test_two_factor_wrong_code_raises_invalid_two_factor_code_error():
    auth, _ = make_auth([FakeResponse(400, cync_error(4001379, "two factor verification code error"))])

    with pytest.raises(InvalidTwoFactorCodeError, match="Invalid two-factor code") as exc_info:
        await auth.login("123456")

    assert isinstance(exc_info.value, AuthFailedError)
    assert exc_info.value.error_code == 4001379


@pytest.mark.asyncio
async def test_two_factor_unknown_error_code_raises_plain_auth_failed_error():
    auth, _ = make_auth([FakeResponse(400, cync_error(4009999, "something else"))])

    with pytest.raises(AuthFailedError) as exc_info:
        await auth.login("123456")

    assert type(exc_info.value) is AuthFailedError
    assert exc_info.value.error_code == 4009999
    assert "4009999" in str(exc_info.value)


@pytest.mark.asyncio
async def test_two_factor_non_json_error_body_raises_plain_auth_failed_error():
    auth, _ = make_auth([FakeResponse(400, raw=b"<html>Bad Request</html>")])

    with pytest.raises(AuthFailedError) as exc_info:
        await auth.login("123456")

    assert type(exc_info.value) is AuthFailedError
    assert exc_info.value.error_code is None


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [
    {"error": {"code": "4001007", "msg": "password error"}},
    {"error": None},
    {"error": "oops"},
    [cync_error(4001007, "password error")],
])
async def test_two_factor_malformed_error_body_raises_plain_auth_failed_error(body):
    auth, _ = make_auth([FakeResponse(400, body)])

    with pytest.raises(AuthFailedError) as exc_info:
        await auth.login("123456")

    assert type(exc_info.value) is AuthFailedError
    assert exc_info.value.error_code is None


@pytest.mark.asyncio
@pytest.mark.parametrize("code, msg", [
    (4001381, "user version error"),
    (4009999, "something else"),
])
async def test_login_without_code_requests_two_factor_email(code, msg):
    auth, session = make_auth([
        FakeResponse(400, cync_error(code, msg)),
        FakeResponse(200, {}),
    ])

    with pytest.raises(TwoFactorRequiredError) as exc_info:
        await auth.login()

    assert exc_info.value.error_code == code
    assert exc_info.value.error_msg == msg
    assert len(session.calls) == 2
    assert session.calls[0]["url"].endswith("/v2/user_auth")
    assert session.calls[1]["url"].endswith("/v2/two_factor/email/verifycode")


@pytest.mark.asyncio
async def test_login_unknown_account_raises_unknown_account_error_without_sending_code():
    auth, session = make_auth([FakeResponse(404, cync_error(4041011, "user not exists"))])

    with pytest.raises(UnknownAccountError) as exc_info:
        await auth.login()

    assert isinstance(exc_info.value, AuthFailedError)
    assert exc_info.value.error_code == 4041011
    assert len(session.calls) == 1


@pytest.mark.asyncio
async def test_login_404_with_other_code_raises_cync_error_with_code():
    auth, _ = make_auth([FakeResponse(404, cync_error(4049999, "something else"))])

    with pytest.raises(CyncError) as exc_info:
        await auth.login()

    assert not isinstance(exc_info.value, AuthFailedError)
    assert exc_info.value.error_code == 4049999
    assert exc_info.value.error_msg == "something else"


@pytest.mark.asyncio
async def test_login_404_with_non_json_body_raises_cync_error():
    auth, _ = make_auth([FakeResponse(404, raw=b"Not Found")])

    with pytest.raises(CyncError) as exc_info:
        await auth.login()

    assert not isinstance(exc_info.value, AuthFailedError)
    assert exc_info.value.error_code is None


@pytest.mark.asyncio
async def test_two_factor_success_returns_user():
    auth, _ = make_auth([FakeResponse(200, TOKENS)])

    user = await auth.login("123456")

    assert isinstance(user, User)
    assert user.access_token == "test_access_token"
    assert user.refresh_token == "test_refresh_token"
    assert user.authorize == "test_authorize"
    assert user.user_id == 123456789
    assert auth.user is user


@pytest.mark.asyncio
async def test_login_server_error_raises_cync_error():
    auth, _ = make_auth([FakeResponse(500, raw=b"Internal Server Error")])

    with pytest.raises(CyncError) as exc_info:
        await auth.login()

    assert not isinstance(exc_info.value, AuthFailedError)


def test_exceptions_constructed_without_error_details():
    bad_request = BadRequestError("Bad Request")
    cync_err = CyncError("x")

    assert str(bad_request) == "Bad Request"
    assert bad_request.error_code is None
    assert bad_request.error_msg is None
    assert str(cync_err) == "x"
    assert cync_err.error_code is None
    assert cync_err.error_msg is None
