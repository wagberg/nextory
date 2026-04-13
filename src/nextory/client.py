"""Main Nextory API client."""

import datetime
import locale as pylocale
import logging
from types import TracebackType
from typing import Any, Optional

import aiohttp

from nextory.exceptions import (
    ERROR_CODE_MAP,
    ExpiredProfileTokenError,
    LibraryApiError,
    NextoryApiError,
    NextoryBackendError,
    NextoryNetowrkError,
    UserApiError,
)
from nextory.models import (
    AccountResponse,
    ApiErrorResponse,
    AudioPackage,
    AutocompleteResponse,
    BookReadingResponse,
    CategoryListResponse,
    HomeEntriesResponse,
    LibraryLists,
    LibraryListType,
    NetworkErrorResponse,
    NextoryApiErrorResponse,
    NextoryBackendErrorResponse,
    PersonResponse,
    ProductResponse,
    ProductsPageResponse,
    ProfilesResponse,
    ProfileTokenResponse,
    ReadingTimeContainerResponse,
    SeriesPageResponse,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.nextory.com"
APP_ID = "200"
APP_VERSION = "2026.04.1"
DEVICE_ID = "q8lDJOBAMKizfHKAnZ0ElA"
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)


COUNTRY_TO_LANG: dict[str, str] = {}


class NextoryClient:
    """Nextory API client for audiobooks.

    Authentication uses two tokens:

    - **login_token**: Deterministic token derived from email/password. Stable across
      logins — the same credentials always produce the same token. Acts more like an
      API key than a session token. Sent as X-Login-Token header.

    - **profile_token**: Session token for the selected profile. Expires periodically
      and is automatically refreshed via login_key when a 401 is received.
      Sent as X-Profile-Token header.

    The login_key identifies which profile to authenticate as and is used to
    refresh the profile_token without re-entering credentials.
    """

    def __init__(
        self,
        login_token: Optional[str] = None,
        login_key: Optional[str] = None,
        profile_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        country: Optional[str] = None,
        base_url: str = BASE_URL,
    ):
        self.login_token = login_token
        self.login_key = login_key
        self.profile_token = profile_token
        self._username = username
        self._password = password
        self._session = session
        self._own_session = session is None
        self._base_url = base_url
        locale = pylocale.getlocale()[0] or "en_US"
        self.country = country or locale.split("_")[-1]
        if country and country in COUNTRY_TO_LANG:
            self._locale = f"{COUNTRY_TO_LANG[country]}_{country}"
        else:
            self._locale = locale
        self._locale_resolved = not country or country in COUNTRY_TO_LANG

    @property
    def auth_headers(self) -> dict[str, str]:
        """Return all auth headers for API requests (also usable by ffmpeg)."""
        headers: dict[str, str] = {
            "X-Application-Id": APP_ID,
            "X-App-Version": APP_VERSION,
            "X-Locale": self._locale,
            "X-Model": "Personal Computer",
            "X-Device-Id": DEVICE_ID,
            "X-Os-Info": "Personal Computer",
        }
        if self.login_token:
            headers["X-Login-Token"] = self.login_token
        if self.country:
            headers["X-Country-Code"] = self.country
        if self.profile_token:
            headers["X-Profile-Token"] = self.profile_token
        return headers

    async def _request(self, method: str, url: str, **kwargs: Any) -> str:
        """Make an authenticated request with error handling and token refresh.

        :param method: HTTP method (GET, POST, PATCH, DELETE).
        :param url: Request URL.
        :returns: Response body text.
        """
        if not self._locale_resolved:
            await self._resolve_locale()
        session = self._get_session()
        for attempt in range(2):
            headers: dict[str, Any] = {**self.auth_headers, **kwargs.pop("headers", {})}
            async with session.request(
                method, url, headers=headers, timeout=DEFAULT_TIMEOUT, **kwargs,
            ) as resp:
                text = await resp.text()
                if resp.ok:
                    return text
                error = self._parse_error(text, resp)
            # Retry once on expired profile token
            if isinstance(error, ExpiredProfileTokenError) and self.login_key and attempt == 0:
                logger.info("Profile token expired, refreshing")
                await self._refresh_profile_token()
                continue
            raise error
        raise RuntimeError("Request failed after retry")

    async def _resolve_locale(self) -> None:
        """Fetch markets API to resolve country→locale mapping."""
        global COUNTRY_TO_LANG  # noqa: PLW0603
        if not COUNTRY_TO_LANG:
            try:
                import json
                session = self._get_session()
                async with session.get(
                    f"{self._base_url}/user/v1.1/markets", headers=self.auth_headers,
                ) as resp:
                    for m in json.loads(await resp.text()):
                        COUNTRY_TO_LANG[m["country_code"]] = m["primary_languages"][0]
            except Exception:
                logger.debug("Failed to fetch markets, using system locale")
        if self.country and self.country in COUNTRY_TO_LANG:
            self._locale = f"{COUNTRY_TO_LANG[self.country]}_{self.country}"
        self._locale_resolved = True

    def _parse_error(self, text: str, resp: aiohttp.ClientResponse) -> Exception:
        """Parse an error response into a typed exception."""
        try:
            err = ApiErrorResponse.from_json(text)
        except Exception:
            logger.warning("Could not parse error response %s: %s", resp.status, text)
            return NextoryNetowrkError(
                resp.status, "Could not parse error response",
                str(resp.url), datetime.datetime.now(),
            )

        if isinstance(err, NetworkErrorResponse):
            return NextoryNetowrkError(resp.status, err.error, err.path, err.timestamp)
        if isinstance(err, NextoryBackendErrorResponse):
            return NextoryBackendError(err.type, err.title, err.status, err.detail, err.instance)
        if not isinstance(err, NextoryApiErrorResponse):
            return ValueError(f"Could not deserialize {text}")

        error = err.error
        error_class = ERROR_CODE_MAP.get(error.code)
        if error_class:
            return error_class(
                code=error.code, key=error.key,
                message=error.message, description=error.description,
            )
        if 3000 <= error.code < 3500:
            return UserApiError(
                code=error.code, key=error.key,
                message=error.message, description=error.description,
            )
        if 5000 <= error.code < 6000:
            return LibraryApiError(
                code=error.code, key=error.key,
                message=error.message, description=error.description,
            )
        logger.warning("Unknown error code %d: %s", error.code, err.to_json())
        return NextoryApiError(
            code=error.code, key=error.key,
            message=error.message, description=error.description,
        )

    async def _refresh_profile_token(self) -> None:
        """Re-authenticate profile using login_key."""
        session = self._get_session()
        url = f"{self._base_url}/user/v1/profile/authorize"
        async with session.post(
            url, headers=self.auth_headers, json={"login_key": self.login_key},
        ) as resp:
            data = await resp.json()
            token = data.get("profile_token")
            if not token:
                raise ValueError(f"Could not refresh profile token: {data}")
            self.profile_token = token

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the client session."""
        if self._own_session and self._session:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    # --- Auth methods ---

    async def login(self, username: str, password: str) -> str:
        """Login and return login token."""
        text = await self._request(
            "POST", f"{self._base_url}/user/v1/sessions",
            json={"identifier": username, "password": password},
        )
        account = AccountResponse.from_json(text)
        if not account.login_token:
            raise ValueError(f"Could not get login token from {text}")
        self.login_token = account.login_token
        return account.login_token

    async def select_profile(self, login_key: str) -> str:
        """Select a profile by login key and return profile token."""
        text = await self._request(
            "POST", f"{self._base_url}/user/v1/profile/authorize",
            json={"login_key": login_key},
        )
        resp = ProfileTokenResponse.from_json(text)
        self.login_key = login_key
        self.profile_token = resp.profile_token
        return resp.profile_token

    # --- Account / profile ---

    async def get_account(self) -> AccountResponse:
        text = await self._request("GET", f"{self._base_url}/user/v1/me/account")
        return AccountResponse.from_json(text)

    async def get_profiles(self) -> ProfilesResponse:
        text = await self._request("GET", f"{self._base_url}/user/v1/me/profiles")
        return ProfilesResponse.from_json(text)

    async def get_subscription(self) -> dict:
        """Get current subscription info.

        :returns: Subscription details (plan, status, expiry, etc.).
        """
        text = await self._request(
            "GET", f"{self._base_url}/obgateway/v1/me/subscription",
        )
        import json
        return json.loads(text)

    async def logout(self) -> None:
        """End the current session.

        Note: The login_token is deterministic and not invalidated by this call.
        This likely just decrements the server-side active session count.
        """
        await self._request("DELETE", f"{self._base_url}/user/v1/sessions")

    # --- Library ---

    async def get_libraries(self) -> LibraryLists:
        """Get user's library lists."""
        text = await self._request(
            "GET", f"{self._base_url}/library/v1/me/library",
            params={"page": 0, "per": 50},
        )
        return LibraryLists.from_json(text)

    async def get_library(
        self, type: LibraryListType, library_id: str, page: int = 0, per: int = 50
    ) -> ProductsPageResponse:
        text = await self._request(
            "GET", f"{self._base_url}/library/v2/me/product_lists/{type}/products",
            params={"id": library_id, "page": page, "per": per},
        )
        return ProductsPageResponse.from_json(text)

    async def get_custom_lists(self, page: int = 0, per: int = 50) -> LibraryLists:
        text = await self._request(
            "GET", f"{self._base_url}/library/v1/me/custom_lists",
            params={"page": page, "per": per},
        )
        return LibraryLists.from_json(text)

    async def add_to_list(self, product_id: int, list_id: str) -> None:
        """Add a product to a list via custom_lists/operations.

        Note: The app uses this endpoint for custom lists. For standard lists
        (ongoing, want_to_read, etc.) it also works but the app uses
        POST /product_lists/{type}/products instead. See remove_from_library
        for the standard list removal counterpart.
        """
        await self._request(
            "POST", f"{self._base_url}/library/v1/me/custom_lists/operations",
            json={"operations": [{"product_id": product_id, "list_id": list_id, "type": "add"}]},
        )

    async def remove_from_list(self, product_id: int, list_id: str) -> None:
        """Remove a product from a list via custom_lists/operations.

        Note: The app uses this endpoint for custom lists only. For standard
        lists (ongoing, want_to_read, etc.) use remove_from_library() instead,
        which uses the DELETE endpoint the app uses for standard lists.
        Both work for standard lists, but this matches the app's intended usage.
        """
        await self._request(
            "POST", f"{self._base_url}/library/v1/me/custom_lists/operations",
            json={"operations": [{"product_id": product_id, "list_id": list_id, "type": "remove"}]},
        )

    async def mark_completed(self, product_id: int) -> None:
        """Mark a product as completed."""
        await self._request(
            "POST", f"{self._base_url}/library/v1/me/products/{product_id}/completed",
        )

    async def unmark_completed(self, product_id: int) -> None:
        """Remove completed status from a product.

        :param product_id: Product ID to unmark.
        """
        await self._request(
            "DELETE", f"{self._base_url}/library/v1/me/products/{product_id}/completed",
        )

    async def add_to_library(self, product_id: int, list_id: str) -> None:
        """Add a product to a library list.

        :param product_id: Product ID to add.
        :param list_id: Target list ID (from get_libraries()).
        """
        await self.add_to_list(product_id, list_id)

    async def remove_from_library(self, product_id: int, list_id: str) -> None:
        """Remove a product from a standard library list (ongoing, want_to_read, etc.).

        Uses DELETE /library/v1/me/product_lists/products. This is the endpoint
        the Android app uses for standard lists (confirmed in decompiled source:
        bb8.java method k, with DeleteProductFromListBody containing listId + productId).

        For custom lists, use remove_from_list() which uses custom_lists/operations.
        Both endpoints work for standard lists, but this matches the app's behavior.

        Despite the name, this only removes from the specified list, not all lists.

        :param product_id: Product ID to remove.
        :param list_id: List ID to remove from (from get_libraries()).
        """
        await self._request(
            "DELETE", f"{self._base_url}/library/v1/me/product_lists/products",
            json={"id": list_id, "product_id": product_id},
        )

    # --- Discovery ---

    async def get_product_details(self, book_id: int) -> ProductResponse:
        text = await self._request(
            "GET", f"{self._base_url}/library/v1/products/{book_id}",
        )
        return ProductResponse.from_json(text)

    async def search_books(
        self, phrase: str, page: int = 0, per: int = 50,
        sort: str = "", showupcoming: bool = True,
    ) -> ProductsPageResponse:
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v1/search/products/books",
            params={
                "search_phrase": phrase, "page": page, "per": per,
                "sort": sort, "showupcoming": str(showupcoming).lower(),
            },
        )
        return ProductsPageResponse.from_json(text)

    async def search_autocomplete(self, phrase: str) -> AutocompleteResponse:
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v1/autocomplete",
            params={"search_phrase": phrase},
        )
        return AutocompleteResponse.from_json(text)

    async def get_author(self, author_id: int) -> PersonResponse:
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v1/author/{author_id}",
        )
        return PersonResponse.from_json(text)

    async def get_narrator(self, narrator_id: int) -> PersonResponse:
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v1/narrator/{narrator_id}",
        )
        return PersonResponse.from_json(text)

    async def get_products_by_path(
        self, path: str, id: int, page: int = 0, per: int = 50,
        content_type: str = "", sort: str = "", showupcoming: bool = False,
    ) -> ProductsPageResponse:
        params: dict[str, Any] = {"page": page, "per": per}
        if content_type:
            params["content_type"] = content_type
        if sort:
            params["sort"] = sort
        if showupcoming:
            params["showupcoming"] = "true"
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v1/{path}/{id}/products",
            params=params,
        )
        return ProductsPageResponse.from_json(text)

    async def popular_magazines(self, page: int = 0, per: int = 50) -> SeriesPageResponse:
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v2/popular/magazines",
            params={"page": page, "per": per},
        )
        return SeriesPageResponse.from_json(text)

    async def popular_series(self, page: int = 0, per: int = 50) -> SeriesPageResponse:
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v2/popular/series",
            params={"page": page, "per": per},
        )
        return SeriesPageResponse.from_json(text)

    async def get_recommendations(
        self, product_id: int, page: int = 0, per: int = 50,
    ) -> ProductsPageResponse:
        """Get recommended products similar to the given product.

        :param product_id: Product ID to base recommendations on.
        :param page: Page number (0-indexed).
        :param per: Items per page.
        """
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v1/recommendations",
            params={"product_id": product_id, "page": page, "per": per},
        )
        return ProductsPageResponse.from_json(text)

    async def get_up_next(
        self, product_id: int, page: int = 0, per: int = 50,
        series_id: Optional[int] = None, author_id: Optional[int] = None,
        format: str = "hls",
    ) -> ProductsPageResponse:
        """Get next suggested product after finishing a book.

        :param product_id: Current product ID.
        :param series_id: Series ID if part of a series.
        :param author_id: Author ID for author-based suggestions.
        :param format: Format filter (e.g. 'hls' for audiobooks).
        """
        params: dict[str, Any] = {
            "product_id": product_id, "page": page, "per": per, "format": format,
        }
        if series_id is not None:
            params["series_id"] = series_id
        if author_id is not None:
            params["author_id"] = author_id
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v1/products/upnext",
            params=params,
        )
        return ProductsPageResponse.from_json(text)

    async def get_series_details(self, series_id: int) -> dict:
        """Get series metadata.

        :param series_id: Series ID.
        :returns: Series details including title, authors, volumes, cover images.
        """
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v2/series/{series_id}",
        )
        import json
        return json.loads(text)

    async def get_home_entries(self, page: int = 0, per: int = 50) -> HomeEntriesResponse:
        """Get home screen entries (recommendations/editorial content).

        :param page: Page number (0-indexed).
        :param per: Items per page.
        """
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v3/home_entries",
            params={"page": page, "per": per},
        )
        return HomeEntriesResponse.from_json(text)

    async def get_home_entry_products(
        self, entry_id: int, page: int = 0, per: int = 20,
    ) -> ProductsPageResponse:
        """Get products for a home screen entry.

        :param entry_id: The home entry id (entry.id, NOT selection.id).
        :param page: Page number (0-indexed).
        :param per: Items per page.
        """
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v3/selections/{entry_id}/products",
            params={"page": page, "per": per},
        )
        return ProductsPageResponse.from_json(text)

    async def get_categories(self, content_type: str = "") -> CategoryListResponse:
        """Get content categories for browsing.

        :param content_type: Filter by content type (e.g. 'book'). Required by the API.
        """
        params: dict[str, Any] = {}
        if content_type:
            params["content_type"] = content_type
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v1/categories",
            params=params,
        )
        return CategoryListResponse.from_json(text)

    async def get_series_products(
        self, series_id: int, content_type: str = "", page: int = 0, per: int = 50,
    ) -> ProductsPageResponse:
        """Get products in a series.

        :param series_id: Series ID.
        :param content_type: Filter by content type (e.g. 'book').
        :param page: Page number (0-indexed).
        :param per: Items per page.
        """
        text = await self._request(
            "GET", f"{self._base_url}/discovery/v1/series/{series_id}/products",
            params={"content_type": content_type, "page": page, "per": per},
        )
        return ProductsPageResponse.from_json(text)

    # --- Reader ---

    async def get_audio_package(self, format_id: int) -> AudioPackage:
        text = await self._request(
            "GET", f"{self._base_url}/reader/books/{format_id}/packages/audio",
        )
        return AudioPackage.from_json(text)

    async def get_bookmarks(self, format_id: int) -> dict:
        """Get bookmarks for a book.

        :param format_id: HLS format identifier.
        """
        text = await self._request(
            "GET", f"{self._base_url}/reader/books/{format_id}/bookmarks",
        )
        import json
        return json.loads(text)

    async def create_bookmark(
        self, profile_id: int, format_id: int, bookmark: dict,
    ) -> dict:
        """Create a bookmark for a book.

        :param profile_id: Profile ID.
        :param format_id: HLS format identifier.
        :param bookmark: Bookmark data (spine_id, position, blurb, etc.).
        """
        text = await self._request(
            "POST",
            f"{self._base_url}/reader/profiles/{profile_id}/books/{format_id}/bookmarks",
            json=bookmark,
        )
        import json
        return json.loads(text)

    async def delete_bookmark(self, bookmark_id: int) -> None:
        """Delete a bookmark.

        :param bookmark_id: Bookmark ID to delete.
        """
        await self._request(
            "DELETE", f"{self._base_url}/reader/bookmarks/{bookmark_id}",
        )

    async def get_audio_preview(self, format_id: int) -> AudioPackage:
        """Get audio preview package for a book.

        :param format_id: HLS format identifier.
        """
        text = await self._request(
            "GET", f"{self._base_url}/reader/books/{format_id}/packages/audio_preview",
        )
        return AudioPackage.from_json(text)

    async def get_position(self, format_id: int) -> BookReadingResponse:
        text = await self._request(
            "GET", f"{self._base_url}/reader/books/{format_id}/position",
        )
        return BookReadingResponse.from_json(text)

    async def patch_position(
        self, profile_id: int, format_id: int,
        percentage: float, elapsed_time: int,
        reached_at: Optional[datetime.datetime] = None,
    ) -> None:
        if reached_at is None:
            reached_at = datetime.datetime.now()
        await self._request(
            "PATCH",
            f"{self._base_url}/reader/profiles/{profile_id}/books/{format_id}/position",
            json={
                "percentage": percentage,
                "elapsed_time": elapsed_time,
                "reached_at": reached_at.isoformat(),
            },
        )

    # --- Reading diary ---

    async def report_usage(
        self, profile_id: int, format_id: int, usage_blocks: list[dict],
    ) -> None:
        """Report playback usage analytics.

        :param profile_id: Profile ID.
        :param format_id: Format identifier (HLS format ID).
        :param usage_blocks: List of usage block dicts with playback progress data.
        """
        await self._request(
            "POST",
            f"{self._base_url}/usageblocks/v1/profile/{profile_id}/format/{format_id}/usage",
            json={"usage_blocks": usage_blocks},
        )

    async def get_reading_time(self, year: int, month: int) -> ReadingTimeContainerResponse:
        text = await self._request(
            "GET", f"{self._base_url}/reading-diary/v1/me/reading_time",
            params={"year": year, "month": month},
        )
        return ReadingTimeContainerResponse.from_json(text)
