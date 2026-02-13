"""Main Nextory API client."""

import datetime
from types import TracebackType
from typing import Any, Optional, Unpack

import aiohttp
from aiohttp.client import _RequestOptions  # type: ignore[attr-defined]
from aiohttp.typedefs import StrOrURL

from nextory.middlewares import (
    NextoryErrorMiddleware,
    NextoryLoginMiddleware,
    NextoryProfileMiddleware,
)
from nextory.models import (
    AccountResponse,
    AudioPackage,
    AutocompleteResponse,
    BookReadingResponse,
    LibraryLists,
    LibraryListType,
    PersonResponse,
    ProductResponse,
    ProductsPageResponse,
    ProfilesResponse,
    ProfileTokenResponse,
    ReadingTimeContainerResponse,
    SeriesPageResponse,
)

BASE_URL = "https://api.nextory.com"


class NextoryClient:
    """Nextory API client for audiobooks."""

    def __init__(
        self,
        login_token: Optional[str] = None,
        login_key: Optional[str] = None,
        profile_token: Optional[str] = None,
        auto_select_profile: bool = False,
        session: Optional[aiohttp.ClientSession] = None,
        country: Optional[str] = None,
        base_url: str = BASE_URL,
    ):
        self._session = session
        self._middlewares = (
            NextoryLoginMiddleware(
                login_token=login_token, country=country
            ),
            NextoryProfileMiddleware(
                auto_select_profile=auto_select_profile,
                login_key=login_key,
                profile_token=profile_token,
            ),
            NextoryErrorMiddleware(),
        )
        self._own_session = session is None
        self._base_url = base_url

    def get(self, url: StrOrURL, **kwargs: Unpack[_RequestOptions]):
        """Make GET request with middlewares."""
        kwargs.setdefault("middlewares", self._middlewares)
        return self._get_session().get(url, **kwargs)

    def post(self, url: StrOrURL, **kwargs: Unpack[_RequestOptions]):
        """Make POST request with middlewares."""
        kwargs.setdefault("middlewares", self._middlewares)
        return self._get_session().post(url, **kwargs)

    def patch(self, url: StrOrURL, **kwargs: Unpack[_RequestOptions]):
        """Make PATCH request with middlewares."""
        kwargs.setdefault("middlewares", self._middlewares)
        return self._get_session().patch(url, **kwargs)

    def delete(self, url: StrOrURL, **kwargs: Unpack[_RequestOptions]):
        """Make DELETE request with middlewares."""
        kwargs.setdefault("middlewares", self._middlewares)
        return self._get_session().delete(url, **kwargs)

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

    @property
    def profile_token(self) -> Optional[str]:
        """Get current profile token."""
        for middleware in self._middlewares:
            if isinstance(middleware, NextoryProfileMiddleware):
                return middleware.profile_token
        return None

    @profile_token.setter
    def profile_token(self, value: Optional[str]) -> None:
        """Set current profile token."""
        for middleware in self._middlewares:
            if isinstance(middleware, NextoryProfileMiddleware):
                middleware.profile_token = value
                return
        raise ValueError("NextoryProfileMiddleware not found in middlewares")

    @property
    def login_token(self) -> Optional[str]:
        """Get current login token."""
        for middleware in self._middlewares:
            if isinstance(middleware, NextoryLoginMiddleware):
                return middleware.login_token
        return None

    @login_token.setter
    def login_token(self, value: Optional[str]) -> None:
        """Set current login token."""
        for middleware in self._middlewares:
            if isinstance(middleware, NextoryLoginMiddleware):
                middleware.login_token = value
                return
        raise ValueError("NextoryLoginMiddleware not found in middlewares")

    @property
    def login_key(self) -> Optional[str]:
        """Get current login key."""
        for middleware in self._middlewares:
            if isinstance(middleware, NextoryProfileMiddleware):
                return middleware.login_key
        return None

    @login_key.setter
    def login_key(self, value: Optional[str]) -> None:
        """Set current login key."""
        for middleware in self._middlewares:
            if isinstance(middleware, NextoryProfileMiddleware):
                middleware.login_key = value
                return
        raise ValueError("NextoryProfileMiddleware not found in middlewares")
    
    async def login(self, username: str, password: str) -> str:
        url = f"{self._base_url}/user/v1/sessions"
        data: dict[str, str] = {
            "identifier": username,
            "password": password,
        }
        async with self.post(url, json=data) as resp:
            text = await resp.text()
            account_response = AccountResponse.from_json(text)
            if not account_response.login_token:
                raise ValueError(f"Could not get login token from {text}")
            self.login_token = account_response.login_token
            return account_response.login_token
            
    async def select_profile(self, login_key: str) -> str:
        """Select a profile by login key."""
        url = f"{self._base_url}/user/v1/profile/authorize"
        async with self.post(
            url,
            json={"login_key": login_key},
        ) as resp:
            data = await resp.text()
            profile_token_response = ProfileTokenResponse.from_json(data)
            self.login_key = login_key
            self.profile_token = profile_token_response.profile_token
            return profile_token_response.profile_token
    
    async def get_reading_time(self, year: int, month: int) -> ReadingTimeContainerResponse:
        url = f"{self._base_url}/reading-diary/v1/me/reading_time"
        params: dict[str, Any] = {
            "year": year,
            "month": month,
        }
        async with self.get(url, params=params) as resp:
            text = await resp.text()
            return ReadingTimeContainerResponse.from_json(text)

    async def get_custom_lists(self, page: int = 0, per: int = 50) -> LibraryLists:
        url = f"{self._base_url}/library/v1/me/custom_lists"
        params: dict[str, int] = {
            "page": page,
            "per": per,
        }
        async with self.get(url, params=params) as resp:
            text = await resp.text()
            return LibraryLists.from_json(text)
    
    async def get_account(self) -> AccountResponse:
        url = f"{self._base_url}/user/v1/me/account"
        async with self.get(url) as resp:
            text = await resp.text()
            return AccountResponse.from_json(text)

    async def get_profiles(self) -> ProfilesResponse:
        url = f"{self._base_url}/user/v1/me/profiles"
        async with self.get(url) as resp:
            text = await resp.text()
            return ProfilesResponse.from_json(text)

    async def popular_magazines(self, page: int = 0, per: int = 50) -> SeriesPageResponse:
        async with self.get(
            f"{self._base_url}/discovery/v2/popular/magazines",
            params={"page": page, "per": per},
        ) as resp:
            text = await resp.text()
            return SeriesPageResponse.from_json(text)

    async def popular_series(self, page: int = 0, per: int = 50) -> SeriesPageResponse:
        async with self.get(
            f"{self._base_url}/discovery/v2/popular/series",
            params={"page": page, "per": per},
        ) as resp:
            text = await resp.text()
            return SeriesPageResponse.from_json(text)

    async def get_libraries(self) -> LibraryLists:
        """Get user's library lists."""
        async with self.get(
            f"{self._base_url}/library/v1/me/library",
            params={"page": 0, "per": 50},
        ) as resp:
            text = await resp.text()
            return LibraryLists.from_json(text)

    async def get_library(
        self, type: LibraryListType, library_id: str, page: int = 0, per: int = 50
    ) -> ProductsPageResponse:
        url = f"{self._base_url}/library/v2/me/product_lists/{type}/products"
        params: dict[str, Any] = {
            "id": library_id,
            "page": page,
            "per": per,
        }
        async with self.get(url, params=params) as resp:
            text = await resp.text()
            return ProductsPageResponse.from_json(text)

    async def get_author(self, author_id: int) -> PersonResponse:
        url = f"{self._base_url}/discovery/v1/author/{author_id}"
        async with self.get(url) as resp:
            text = await resp.text()
            return PersonResponse.from_json(text)

    async def get_narrator(self, narrator_id: int) -> PersonResponse:
        url = f"{self._base_url}/discovery/v1/narrator/{narrator_id}"
        async with self.get(url) as resp:
            text = await resp.text()
            return PersonResponse.from_json(text)

    async def get_products_by_path(
        self,
        path: str,
        id: int,
        page: int = 0,
        per: int = 50,
        content_type: str = "",
        sort: str = "",
        showupcoming: bool = False,
    ) -> ProductsPageResponse:
        # sort: volume
        url = f"{self._base_url}/discovery/v1/{path}/{id}/products"
        params: dict[str, Any] = {
            "page": page,
            "per": per,
            "content_type": content_type,
            "sort": sort,
            "showupcoming": str(showupcoming).lower(),
        }
        async with self.get(url, params=params) as resp:
            text = await resp.text()
            try:
                products_page_response = ProductsPageResponse.from_json(text)
            except Exception:
                print(f"Failed to parse response: {text}")
                raise
            return products_page_response

    async def search_autocomplete(self, phrase: str) -> AutocompleteResponse:
        url = f"{self._base_url}/discovery/v1/autocomplete"
        params: dict[str, Any] = {
            "search_phrase": phrase,
        }
        async with self.get(url, params=params) as resp:
            text = await resp.text()
            return AutocompleteResponse.from_json(text)

    async def search_books(
        self, phrase: str, page: int = 0, per: int = 50, sort: str = "", showupcoming: bool = True
    ) -> ProductsPageResponse:
        # From error response
        # (18 known properties: "authors_facet", "narrators_facet", "formattype_facet",
        # "narratorslug_facet", "authorslug_facet", "page", "language_facet", "categoryids_facet",
        # "format", "language", "showupcoming", "seriesslug_facet", "per", "sort", "series_facet",
        # "search_phrase", "avgrate_min_facet", "avgrate_max_facet"])
        # sort can be relevance
        # format can be ebook,audiobook
        url = f"{self._base_url}/discovery/v1/search/products/books"
        params: dict[str, Any] = {
            "search_phrase": phrase,
            "page": page,
            "per": per,
            "sort": sort,
            "showupcoming": str(showupcoming).lower(),
        }
        async with self.get(url, params=params) as resp:
            text = await resp.text()
            return ProductsPageResponse.from_json(text)

    async def get_product_details(self, book_id: int) -> ProductResponse:
        async with self.get(
            f"{self._base_url}/library/v1/products/{book_id}",
        ) as resp:
            text = await resp.text()
            return ProductResponse.from_json(text)

    async def get_audio_package(self, format_id: int) -> AudioPackage:
        url = f"{self._base_url}/reader/books/{format_id}/packages/audio"
        async with self.get(url) as resp:
            text = await resp.text()
            return AudioPackage.from_json(text)

    async def get_position(self, format_id: int) -> BookReadingResponse:
        url = f"{self._base_url}/reader/books/{format_id}/position"
        async with self.get(url) as resp:
            text = await resp.text()
            return BookReadingResponse.from_json(text)

    async def patch_position(
        self,
        profile_id: int,
        format_id: int,
        percentage: float,
        elapsed_time: int,
        reached_at: Optional[datetime.datetime] = None,
    ) -> None:
        if reached_at is None:
            reached_at = datetime.datetime.now()
        url = f"{self._base_url}/reader/profiles/{profile_id}/books/{format_id}/position"
        data: dict[str, Any] = {
            "percentage": percentage,
            "elapsed_time": elapsed_time,
            "reached_at": reached_at.isoformat(),
        }
        await self.patch(url, json=data)
