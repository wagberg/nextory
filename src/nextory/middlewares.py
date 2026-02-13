"""Middleware components for Nextory API client."""

import asyncio
import datetime
import locale as pylocale
import logging
from typing import Optional

import aiohttp

from nextory.exceptions import (
    ExpiredLoginTokenError,
    ExpiredProfileTokenError,
    InvalidAuthTokenError,
    InvalidDataError,
    LibraryApiError,
    MissingHeaderError,
    MissingParameterError,
    NextoryApiError,
    NextoryBackendError,
    NextoryNetowrkError,
    ProfileNotFoundError,
    UnauthorizedError,
    UserApiError,
    UserNotAuthenticatedError,
)
from nextory.models import (
    ApiErrorResponse,
    NetworkErrorResponse,
    NextoryApiErrorResponse,
    NextoryBackendErrorResponse,
)

logger = logging.getLogger(__name__)

APP_ID = "200"
APP_VERSION = "2026.01.3"
# DEVICE_ID = "abc94324-e040-30a8-b37c-72809d9d0494" # Old format
DEVICE_ID = "q8lDJOBAMKizfHKAnZ0ElA" # New format from same data

class NextoryLoginMiddleware:
    """Middleware for device authentication and login token management.

    Automatically handles login token refresh when expired and manages country code.
    """

    def __init__(
        self,
        login_token: Optional[str] = None,
        country: Optional[str] = None,
        locale: Optional[str] = None,
    ):
        self._login_token = login_token
        
        self._lock = asyncio.Lock()
        locale = locale or pylocale.getlocale()[0] or "en_US"
        self._country: Optional[str] = country or locale.split("_")[-1]
        
        self._headers = {
            "X-Application-Id": APP_ID,
            "X-App-Version": APP_VERSION,
            "X-Locale": locale,
            "X-Model": "Personal Computer",
            "X-Device-Id": DEVICE_ID,
            "X-Os-Info": "Personal Computer",
        }

    async def __call__(
        self, req: aiohttp.ClientRequest, handler: aiohttp.ClientHandlerType
    ) -> aiohttp.ClientResponse:
        req.headers.update(self._headers)
        if self._login_token:
            req.headers["X-Login-Token"] = self._login_token
        if self._country:
            req.headers["X-Country-Code"] = self._country

        logger.debug(
            "%s %s headers: %s",
            req.method,
            req.url,
            dict(req.headers)
        )

        try:
            resp = await handler(req)
        except MissingHeaderError as e:
            logger.warning(
                "%s: %s", type(e).__name__, e
            )
            if "xcountrycode" in e.missing_headers:
                await self._update_country(req)
            else:
                raise
        
        return resp

    @property
    def login_token(self) -> Optional[str]:
        """Get current login token."""
        return self._login_token

    @login_token.setter
    def login_token(self, value: Optional[str]) -> None:
        """Set current login token."""
        self._login_token = value

    @property
    def country(self) -> Optional[str]:
        """Get country code."""
        return self._country
    
    @country.setter
    def country(self, value: str) -> None:
        """Set country code."""
        self._country = value

    async def _update_country(self, req: aiohttp.ClientRequest):
        url = req.url.with_path("user/v1/me/account")
        async with req.session.get(url, headers=req.headers) as resp:
            data = await resp.json()
            self._country = data.get("country")

class NextoryProfileMiddleware:
    """Middleware for profile authentication and profile token management.

    Automatically handles profile token refresh when expired.
    """

    def __init__(
        self,
        auto_select_profile: bool = False,
        login_key: Optional[str] = None,
        profile_token: Optional[str] = None,
    ):
        if not auto_select_profile and not login_key:
            raise ValueError("Must provide login_key when auto_select_profile = False")
        self._auto_select_profile = auto_select_profile
        self._login_key = login_key
        self._profile_token = profile_token
        self._lock = asyncio.Lock()

    @property
    def profile_token(self) -> Optional[str]:
        """Get current profile token."""
        return self._profile_token

    @profile_token.setter
    def profile_token(self, value: Optional[str]) -> None:
        """Set current profile token."""
        self._profile_token = value

    @property
    def login_key(self) -> Optional[str]:
        """Get current login key."""
        return self._login_key

    @login_key.setter
    def login_key(self, value: Optional[str]) -> None:
        """Set current login key."""
        self._login_key = value

    async def __call__(
        self, req: aiohttp.ClientRequest, handler: aiohttp.ClientHandlerType
    ) -> aiohttp.ClientResponse:
        resp = None
        for _ in range(2):
            req.headers.update(
                {
                    "X-Profile-Token": self._profile_token or "0",
                }
            )
            logger.debug(
                "%s %s headers: %s",
                req.method,
                req.url,
                dict(req.headers),
                extra={"class": self.__class__.__name__},
            )

            try:
                resp = await handler(req)
                break
            except NextoryApiError as e:
                if isinstance(e, (ProfileNotFoundError, InvalidAuthTokenError)) or (
                    isinstance(e, MissingHeaderError) and "X-Profile-Token" in e.description
                ):
                    # ProfileNotFoundError -> login_key correct format for not found
                    # InvalidAuthTokenError -> login_key has wrong format.
                    logger.warning(
                        "%s: %s", type(e).__name__, e, extra={"class": self.__class__.__name__}
                    )
                    profiles = await self._list_profiles(req)
                    if not self._auto_select_profile:
                        raise ValueError(
                            f"Could not find profile. Available profiles: {profiles}"
                        ) from e
                    # Pick the first profile
                    profile_name, self._login_key = next(iter(profiles.items()))
                    logger.info(
                        f"Auto-selected profile {profile_name}",
                        extra={"class": self.__class__.__name__},
                    )
                elif not isinstance(e, ExpiredProfileTokenError):
                    raise
                else:
                    logger.warning(
                        "%s: %s", type(e).__name__, e, extra={"class": self.__class__.__name__}
                    )
                await self._login_profile(req)

        if resp is None:
            raise RuntimeError("Could not handle request")
        return resp

    async def _list_profiles(self, req: aiohttp.ClientRequest):
        logger.debug("Listing profiles", extra={"class": self.__class__.__name__})
        url = req.url.with_path("user/v1/me/profiles")
        async with req.session.get(
            url,
            headers=req.headers,
        ) as resp:
            data = await resp.json()
            logger.debug("Profiles response: %s", data, extra={"class": self.__class__.__name__})
            return {
                f"{profile['name']} {profile['surname']}": profile["login_key"]
                for profile in data["profiles"]
            }

    async def _login_profile(self, req: aiohttp.ClientRequest):
        token = self._profile_token
        async with self._lock:
            if token != self._profile_token:
                return
            url = req.url.with_path("user/v1/profile/authorize")
            logger.debug(
                "Selecting profile. POST to %s with login_key %s",
                url,
                self._login_key,
                extra={"class": self.__class__.__name__},
            )
            async with req.session.post(
                url,
                headers=req.headers,
                json={"login_key": self._login_key},
            ) as resp:
                data = await resp.json()
                profile_token = data.get("profile_token")
                logger.debug(
                    "Selected profile. Got profile_token %s",
                    profile_token,
                )
                if not profile_token:
                    raise ValueError(f"Could not get profile token from {data}")
                self._profile_token = profile_token


ERROR_CODE_MAP: dict[int, type[NextoryApiError]] = {
    1001: InvalidAuthTokenError,
    1002: UserNotAuthenticatedError,
    1005: MissingHeaderError,
    1006: MissingParameterError,
    1007: InvalidDataError,
    2001: ExpiredLoginTokenError,
    2002: ExpiredProfileTokenError,
    3010: ProfileNotFoundError,
    7111: UnauthorizedError,
}


class NextoryErrorMiddleware:
    """Middleware for parsing API error responses and raising typed exceptions."""

    async def __call__(
        self, req: aiohttp.ClientRequest, handler: aiohttp.ClientHandlerType
    ) -> aiohttp.ClientResponse:
        logger.debug(
            "%s %s headers: %s",
            req.method,
            req.url,
            dict(req.headers),
        )
        resp = await handler(req)
        if resp.ok:
            return resp

        data = await resp.text()
        try:
            err = ApiErrorResponse.from_json(data)
        except Exception:
            logger.warning("Could not parse error response %s: %s", resp.status, data)
            raise NextoryNetowrkError(
                resp.status,
                "Could not parse error response",
                str(resp.url),
                datetime.datetime.now(),
            )

        if isinstance(err, NetworkErrorResponse):
            raise NextoryNetowrkError(resp.status, err.error, err.path, err.timestamp)
        if isinstance(err, NextoryBackendErrorResponse):
            raise NextoryBackendError(err.type, err.title, err.status, err.detail, err.instance)
        if not isinstance(err, NextoryApiErrorResponse):
            raise ValueError(f"Could not deserialize {data}")

        error = err.error
        error_class = ERROR_CODE_MAP.get(error.code)

        if error_class:
            raise error_class(
                code=error.code, key=error.key, message=error.message, description=error.description
            )
        elif 3000 <= error.code < 3500:
            raise UserApiError(
                code=error.code, key=error.key, message=error.message, description=error.description
            )
        elif 5000 <= error.code < 6000:
            raise LibraryApiError(
                code=error.code, key=error.key, message=error.message, description=error.description
            )
        else:
            logger.warning("Unknown error code %d: %s", error.code, err.to_json())
            raise NextoryApiError(
                code=error.code, key=error.key, message=error.message, description=error.description
            )
