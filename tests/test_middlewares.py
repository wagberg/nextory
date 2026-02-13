"""Tests for middleware components."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from nextory.exceptions import (
    ExpiredLoginTokenError,
    ExpiredProfileTokenError,
    InvalidAuthTokenError,
    LibraryApiError,
    MissingHeaderError,
    NextoryApiError,
    NextoryNetowrkError,
    ProfileNotFoundError,
    UserApiError,
)
from nextory.middlewares import (
    NextoryErrorMiddleware,
    NextoryLoginMiddleware,
    NextoryProfileMiddleware,
)


def make_response(status: int = 200, text: str = "{}"):
    """Create a mock aiohttp response."""
    resp = MagicMock()
    resp.ok = status < 400
    resp.status = status
    resp.text = AsyncMock(return_value=text)
    resp.json = AsyncMock(return_value={} if text == "{}" else None)
    return resp


def make_request(session=None):
    """Create a mock aiohttp request."""
    req = MagicMock()
    req.method = "GET"
    req.url = MagicMock()
    req.url.with_path = MagicMock(return_value="https://api.nextory.com/test")
    req.headers = {}
    req.session = session or MagicMock()
    return req


class TestNextoryErrorMiddleware:
    """Tests for NextoryErrorMiddleware."""

    @pytest.mark.asyncio
    async def test_passes_through_ok_response(self):
        middleware = NextoryErrorMiddleware()
        req = make_request()
        handler = AsyncMock(return_value=make_response(200))

        result = await middleware(req, handler)

        assert result.status == 200

    @pytest.mark.asyncio
    async def test_raises_network_error(self):
        """Real API response from /library/v1/me/library."""
        middleware = NextoryErrorMiddleware()
        req = make_request()
        error_json = '{"timestamp": "2026-01-29T10:25:42.751+00:00", "status": 400, "error": "Bad Request", "path": "/library/v1/me/library"}'
        handler = AsyncMock(return_value=make_response(400, error_json))

        with pytest.raises(NextoryNetowrkError) as exc:
            await middleware(req, handler)

        assert exc.value.status == 400
        assert exc.value.error == "Bad Request"
        assert exc.value.path == "/library/v1/me/library"

    @pytest.mark.asyncio
    async def test_raises_expired_login_token_error(self):
        """Real API response for expired login token."""
        middleware = NextoryErrorMiddleware()
        req = make_request()
        error_json = '{"error": {"code": 2001, "key": "LoginTokenExpired", "description": "Login token is invalid or unable to decode", "message": "Du kunde inte logga in. Försök igen senare."}}'
        handler = AsyncMock(return_value=make_response(401, error_json))

        with pytest.raises(ExpiredLoginTokenError) as exc:
            await middleware(req, handler)

        assert exc.value.code == 2001
        assert exc.value.key == "LoginTokenExpired"

    @pytest.mark.asyncio
    async def test_raises_expired_profile_token_error(self):
        """Real API response for expired profile token."""
        middleware = NextoryErrorMiddleware()
        req = make_request()
        error_json = '{"error": {"code": 2002, "key": "ProfileTokenExpiredSameProfile", "message": "Error.ProfileTokenExpiredSameProfile", "description": "Profile token validity expired or invalid state due to same profile logged in on other device"}}'
        handler = AsyncMock(return_value=make_response(401, error_json))

        with pytest.raises(ExpiredProfileTokenError) as exc:
            await middleware(req, handler)

        assert exc.value.code == 2002

    @pytest.mark.asyncio
    async def test_raises_missing_header_error_login_token(self):
        """Real API response for missing X-Profile-Token header."""
        middleware = NextoryErrorMiddleware()
        req = make_request()
        error_json = '{"error": {"code": 1005, "key": "MandatoryHeaderMissing", "message": "Something went wrong. Try again later or contact us. Error code: 1005", "description": "Mandatory header fields [X-Profile-Token] missing"}}'
        handler = AsyncMock(return_value=make_response(400, error_json))

        with pytest.raises(MissingHeaderError) as exc:
            await middleware(req, handler)

        assert "X-Profile-Token" in exc.value.description

    @pytest.mark.asyncio
    async def test_raises_missing_header_error_multiple(self):
        """Real API response for multiple missing headers."""
        middleware = NextoryErrorMiddleware()
        req = make_request()
        error_json = '{"error": {"code": 1005, "key": "MandatoryHeaderMissing", "message": "Something went wrong. Try again later or contact us. Error code: 1005", "description": "Mandatory header fields [X-Profile-Token, xCountryCode] missing"}}'
        handler = AsyncMock(return_value=make_response(400, error_json))

        with pytest.raises(MissingHeaderError) as exc:
            await middleware(req, handler)

        assert "xCountryCode" in exc.value.description

    @pytest.mark.asyncio
    async def test_raises_user_not_authenticated_error(self):
        """Real API response for missing authorization token."""
        middleware = NextoryErrorMiddleware()
        req = make_request()
        error_json = '{"error": {"code": 1002, "key": "UserNotAuthenticated", "description": "Authorization token is missing ", "message": "Något gick fel. Försök igen senare eller kontakta oss. Felkod: {0}"}}'
        handler = AsyncMock(return_value=make_response(401, error_json))

        from nextory.exceptions import UserNotAuthenticatedError

        with pytest.raises(UserNotAuthenticatedError) as exc:
            await middleware(req, handler)

        assert exc.value.code == 1002

    @pytest.mark.asyncio
    async def test_raises_invalid_auth_token_error(self):
        """Real API response for invalid auth token (code 1001)."""
        middleware = NextoryErrorMiddleware()
        req = make_request()
        error_json = '{"error": {"code": 1001, "key": "Unauthorized", "message": "Something went wrong. Try again later or contact us. Error code: 1001", "description": "authorization exception"}}'
        handler = AsyncMock(return_value=make_response(401, error_json))

        with pytest.raises(InvalidAuthTokenError) as exc:
            await middleware(req, handler)

        assert exc.value.code == 1001

    @pytest.mark.asyncio
    async def test_raises_user_api_error_for_user_not_found(self):
        """Real API response for user not found (code 3009)."""
        middleware = NextoryErrorMiddleware()
        req = make_request()
        error_json = '{"error": {"code": 3009, "key": "UserNotFound", "description": "Account doesn\'t exists with input identifier", "message": "Dubbelkolla lösenordet."}}'
        handler = AsyncMock(return_value=make_response(400, error_json))

        with pytest.raises(UserApiError) as exc:
            await middleware(req, handler)

        assert exc.value.code == 3009

    @pytest.mark.asyncio
    async def test_raises_library_api_error_for_product_list_error(self):
        """Real API response for product list error (code 5022)."""
        middleware = NextoryErrorMiddleware()
        req = make_request()
        error_json = '{"error": {"code": 5022, "key": "ProductListError", "message": "Something went wrong. Try again later or contact us. Error code: 5022", "description": "ListId is not matching with type"}}'
        handler = AsyncMock(return_value=make_response(422, error_json))

        with pytest.raises(LibraryApiError) as exc:
            await middleware(req, handler)

        assert exc.value.code == 5022

    @pytest.mark.asyncio
    async def test_raises_generic_api_error_for_unknown_codes(self):
        middleware = NextoryErrorMiddleware()
        req = make_request()
        error_json = '{"error": {"code": 9999, "key": "unknown", "message": "Unknown", "description": "Unknown error"}}'
        handler = AsyncMock(return_value=make_response(400, error_json))

        with pytest.raises(NextoryApiError) as exc:
            await middleware(req, handler)

        assert exc.value.code == 9999


class TestNextoryLoginMiddleware:
    """Tests for NextoryLoginMiddleware."""

    @pytest.mark.asyncio
    async def test_adds_headers_to_request(self):
        middleware = NextoryLoginMiddleware(
            username="test@example.com",
            password="password",
            login_token="test_token",
            country="GB",
        )
        req = make_request()
        handler = AsyncMock(return_value=make_response(200))

        await middleware(req, handler)

        assert req.headers["X-Login-Token"] == "test_token"
        assert req.headers["X-Country-Code"] == "GB"

    @pytest.mark.asyncio
    async def test_refreshes_token_on_expired_error(self):
        middleware = NextoryLoginMiddleware(
            username="test@example.com",
            password="password",
            login_token="old_token",
        )

        # Mock session for login request
        login_resp = MagicMock()
        login_resp.__aenter__ = AsyncMock(
            return_value=MagicMock(
                json=AsyncMock(return_value={"login_token": "new_token", "country": "GB"})
            )
        )
        login_resp.__aexit__ = AsyncMock()

        session = MagicMock()
        session.post = MagicMock(return_value=login_resp)

        req = make_request(session)

        call_count = 0

        async def handler_side_effect(r):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ExpiredLoginTokenError(2001, "expired", "Expired", "Token expired")
            return make_response(200)

        handler = AsyncMock(side_effect=handler_side_effect)

        await middleware(req, handler)

        assert middleware._login_token == "new_token"
        assert middleware._country == "GB"


class TestNextoryProfileMiddleware:
    """Tests for NextoryProfileMiddleware."""

    def test_requires_login_key_when_not_auto_select(self):
        with pytest.raises(ValueError, match="Must provide login_key"):
            NextoryProfileMiddleware(auto_select_profile=False, login_key=None)

    @pytest.mark.asyncio
    async def test_adds_profile_token_header(self):
        middleware = NextoryProfileMiddleware(
            login_key="test_key",
            profile_token="test_profile_token",
        )
        req = make_request()
        handler = AsyncMock(return_value=make_response(200))

        await middleware(req, handler)

        assert req.headers["X-Profile-Token"] == "test_profile_token"

    @pytest.mark.asyncio
    async def test_refreshes_profile_token_on_expired(self):
        middleware = NextoryProfileMiddleware(
            login_key="test_key",
            profile_token="old_token",
        )

        # Mock session for profile login
        profile_resp = MagicMock()
        profile_resp.__aenter__ = AsyncMock(
            return_value=MagicMock(
                json=AsyncMock(return_value={"profile_token": "new_profile_token"})
            )
        )
        profile_resp.__aexit__ = AsyncMock()

        session = MagicMock()
        session.post = MagicMock(return_value=profile_resp)

        req = make_request(session)

        call_count = 0

        async def handler_side_effect(r):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ExpiredProfileTokenError(2002, "expired", "Expired", "Profile token expired")
            return make_response(200)

        handler = AsyncMock(side_effect=handler_side_effect)

        await middleware(req, handler)

        assert middleware._profile_token == "new_profile_token"

    @pytest.mark.asyncio
    async def test_auto_select_profile_on_not_found(self):
        middleware = NextoryProfileMiddleware(
            auto_select_profile=True,
            login_key="wrong_key",
        )

        # Mock profiles list response
        profiles_resp = MagicMock()
        profiles_resp.__aenter__ = AsyncMock(
            return_value=MagicMock(
                json=AsyncMock(
                    return_value={
                        "profiles": [{"name": "John", "surname": "Doe", "login_key": "correct_key"}]
                    }
                )
            )
        )
        profiles_resp.__aexit__ = AsyncMock()

        # Mock profile login response
        login_resp = MagicMock()
        login_resp.__aenter__ = AsyncMock(
            return_value=MagicMock(json=AsyncMock(return_value={"profile_token": "new_token"}))
        )
        login_resp.__aexit__ = AsyncMock()

        session = MagicMock()
        session.get = MagicMock(return_value=profiles_resp)
        session.post = MagicMock(return_value=login_resp)

        req = make_request(session)

        call_count = 0

        async def handler_side_effect(r):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ProfileNotFoundError(3010, "not_found", "Not found", "Profile not found")
            return make_response(200)

        handler = AsyncMock(side_effect=handler_side_effect)

        await middleware(req, handler)

        assert middleware._login_key == "correct_key"
        assert middleware._profile_token == "new_token"

    @pytest.mark.asyncio
    async def test_raises_when_profile_not_found_and_no_auto_select(self):
        middleware = NextoryProfileMiddleware(
            auto_select_profile=False,
            login_key="wrong_key",
        )

        # Mock profiles list response
        profiles_resp = MagicMock()
        profiles_resp.__aenter__ = AsyncMock(
            return_value=MagicMock(
                json=AsyncMock(
                    return_value={
                        "profiles": [{"name": "John", "surname": "Doe", "login_key": "correct_key"}]
                    }
                )
            )
        )
        profiles_resp.__aexit__ = AsyncMock()

        session = MagicMock()
        session.get = MagicMock(return_value=profiles_resp)

        req = make_request(session)
        handler = AsyncMock(
            side_effect=ProfileNotFoundError(3010, "not_found", "Not found", "Profile not found")
        )

        with pytest.raises(ValueError, match="Could not find profile"):
            await middleware(req, handler)
