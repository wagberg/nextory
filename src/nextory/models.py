"""Data models for Nextory API responses."""

import datetime
import enum
from dataclasses import dataclass, field
from typing import Optional, TypeAlias

from mashumaro.config import BaseConfig
from mashumaro.mixins.json import DataClassJSONMixin
from mashumaro.types import Discriminator, SerializationStrategy

Url: TypeAlias = str


@dataclass
class Profile(DataClassJSONMixin):
    """User profile information."""

    id: int
    name: str
    login_key: str
    is_main: bool


@dataclass
class AudioFile(DataClassJSONMixin):
    """Audio file information from audio package."""

    idref: str
    uri: str
    start_at: int
    end_at: int
    duration: int
    title: Optional[str] = None
    file_id: Optional[str] = None


@dataclass
class AudioCryptKeyResponse(DataClassJSONMixin):
    """Audio encryption key information."""

    key: str
    url: str


@dataclass
class AudioPackage(DataClassJSONMixin):
    """Audio package containing list of audio files."""

    duration: int
    files: list[AudioFile]
    crypt_keys: Optional[list[AudioCryptKeyResponse]] = None
    sliced_at: Optional[datetime.datetime] = None


@dataclass
class Author(DataClassJSONMixin):
    """Author information."""

    name: str
    id: Optional[int] = None


@dataclass
class Narrator(DataClassJSONMixin):
    """Narrator information."""

    name: str
    id: Optional[int] = None


@dataclass
class Format(DataClassJSONMixin):
    """Book format information."""

    type: str
    identifier: int
    img_url: Optional[str] = None


@dataclass
class Audiobook(DataClassJSONMixin):
    """Audiobook metadata."""

    id: int
    title: str
    authors: list[Author]
    narrators: list[Narrator]
    formats: list[Format]
    description_full: Optional[str] = None
    duration: Optional[int] = None


@dataclass
class ReadingPosition(DataClassJSONMixin):
    """Current reading position for a book."""

    percentage: float
    reached_at: str
    elapsed_time: Optional[int] = None
    page_number: Optional[int] = None
    path: Optional[str] = None
    idref: Optional[str] = None


@dataclass
class UsageBlock(DataClassJSONMixin):
    """Usage block for reporting playback progress."""

    format_type: str
    start_percentage: float
    end_percentage: float
    start_time: int
    end_time: int
    start_duration: Optional[float] = None
    end_duration: Optional[float] = None
    player_speed: Optional[float] = None
    source: Optional[str] = None
    mode: Optional[str] = None


class ProductType(enum.StrEnum):
    BOOK = "book"
    MAGAZINE = "magazine"


class LibraryFilterType(enum.StrEnum):
    BOOLEAN = "Boolean"
    STRING = "String"
    INTEGER = "Integer"
    UNKNOWN = "Unknown"


@dataclass
class LibraryFilterOptionResponse(DataClassJSONMixin):
    name: str
    display_name: str


@dataclass
class LibraryFilterResponse(DataClassJSONMixin):
    name: str
    display_name: str
    type: LibraryFilterType
    allowed_values: list[LibraryFilterOptionResponse]


class LibraryListType(enum.StrEnum):
    AUTHOR = "author"
    BRAND_SUBSCRIPTION = "brand_subscription"
    COMPLETED = "completed"
    CUSTOM = "custom"
    DOWNLOADED = "downloaded"
    OFFLINE = "offline"
    ONGOING = "ongoing"
    FOLLOWING = "following"
    PURCHASED = "purchased"
    WANT_TO_READ = "want_to_read"
    UNKNOWN = "unknown"


@dataclass
class LibraryList(DataClassJSONMixin):
    """Library list information."""

    id: str
    offline_available: bool
    editable: bool
    deletable: bool
    is_content_frozen: bool
    type: LibraryListType
    created_date: datetime.datetime
    name: Optional[str] = None
    item_count: Optional[int] = None
    book_count: Optional[int] = None
    cover_images: Optional[list[Url]] = None
    content_type: Optional[list[ProductType]] = None
    filters: Optional[list[LibraryFilterResponse]] = None
    latest_edition_date: Optional[str] = None


@dataclass
class LibraryLists(DataClassJSONMixin):
    """User library lists."""

    product_lists: list[LibraryList] = field(default_factory=list[LibraryList])
    lists: Optional[list[LibraryList]] = field(default=None)


@dataclass
class NextoryApiError(DataClassJSONMixin):
    """Network API error response."""

    code: int
    key: str
    message: str
    description: str


@dataclass
class ApiErrorResponse(DataClassJSONMixin):
    class Config(BaseConfig):
        discriminator = Discriminator(include_subtypes=True)


@dataclass
class NextoryApiErrorResponse(ApiErrorResponse):
    error: NextoryApiError


@dataclass
class NetworkErrorResponse(ApiErrorResponse):
    timestamp: datetime.datetime
    status: int
    error: str
    path: str


@dataclass
class NextoryBackendErrorResponse(ApiErrorResponse):
    type: str
    title: str
    status: int
    detail: str
    instance: str


@dataclass
class ShortAuthorResponse(DataClassJSONMixin):
    id: int
    name: str


@dataclass
class ShortNarratorResponse(DataClassJSONMixin):
    id: int
    name: str


@dataclass
class Series(DataClassJSONMixin):
    id: int
    name: str


@dataclass
class ShortPublisherResponse(DataClassJSONMixin):
    id: int
    name: str


@dataclass
class FormatReadingResponse(DataClassJSONMixin):
    latest: bool
    percentage: Optional[float] = None
    ojd_link: Optional[str] = None


@dataclass
class ShortTranslatorResponse(DataClassJSONMixin):
    id: int
    name: str


@dataclass
class AccessibilityFeatureResponse(DataClassJSONMixin):
    title: str
    details: Optional[list[str]] = None


class FormatType(enum.StrEnum):
    EPUB = "epub"
    HLS = "hls"
    PDF = "pdf"


@dataclass
class FormatResponse(DataClassJSONMixin):
    identifier: int
    type: FormatType
    img_url: str
    publisher: ShortPublisherResponse
    cover_ratio: float
    state: str
    free: bool
    purchased: bool
    time_limited: bool
    preview: bool
    translators: list[ShortTranslatorResponse] = field(
        default_factory=list[ShortTranslatorResponse]
    )
    publication_date: Optional[datetime.date] = None
    pages: Optional[int] = None
    duration: Optional[int] = None
    cover_color: Optional[str] = None
    readings: Optional[FormatReadingResponse] = None
    publisher_price_total: Optional[float] = None
    publisher_price_per_page: Optional[float] = None
    read_and_listen: Optional[bool] = None
    accessibility_features: list[AccessibilityFeatureResponse] = field(
        default_factory=list[AccessibilityFeatureResponse]
    )


@dataclass
class ProfileProductResponse(DataClassJSONMixin):
    in_library: bool
    is_completed: bool
    is_ongoing: bool
    referral_url: Optional[str] = None


@dataclass
class ProductBadgeResponse(DataClassJSONMixin):
    short_label: str
    long_label: str
    type: str


@dataclass
class ProductResponse(DataClassJSONMixin):
    id: int
    title: str
    media_type: str
    is_adult_book: bool
    average_rating: float
    number_of_rates: int
    language: str
    authors: list[ShortAuthorResponse]
    narrators: list[ShortNarratorResponse]
    formats: list[FormatResponse]
    profile_product: ProfileProductResponse
    blurb: Optional[str] = None
    description_full: Optional[str] = None
    esales_ticket: Optional[str] = None
    share_url: Optional[str] = None
    volume: Optional[int] = None
    series: Optional[Series] = None
    product_badges: Optional[list[ProductBadgeResponse]] = None
    is_format_synced: Optional[bool] = None


@dataclass
class CoverImageResponse(DataClassJSONMixin):
    cover_image: str
    cover_ratio: float
    cover_color: Optional[str] = None


@dataclass
class SortFieldResponse(DataClassJSONMixin):
    field: str
    default: bool


@dataclass
class SocialMetaInfoResponse(DataClassJSONMixin):
    followers: int
    notify: bool
    subscribed: bool


@dataclass
class SubCategoryResponse(DataClassJSONMixin):
    id: int
    large_image: str
    products_count: int
    small_image: str
    sub_categories: list["SubCategoryResponse"]
    title: str
    bgc: Optional[str] = None


@dataclass
class CategoryResponse(DataClassJSONMixin):
    id: int
    title: str
    show_filter: Optional[bool] = None
    sort_fields: list[SortFieldResponse] = field(default_factory=list[SortFieldResponse])
    sub_categories: list[SubCategoryResponse] = field(default_factory=list[SubCategoryResponse])
    products_count: Optional[int] = None
    content_type: Optional[str] = None
    bgc: Optional[str] = None
    large_image: Optional[str] = None
    small_image: Optional[str] = None


@dataclass
class CategoryListResponse(DataClassJSONMixin):
    """Response from GET /discovery/v1/categories."""

    categories: list[CategoryResponse]


@dataclass
class HomeSelectionResponse(DataClassJSONMixin):
    """Selection within a home entry."""

    id: int
    title: str
    type: Optional[str] = None
    detail: Optional[str] = None
    small_image: Optional[str] = None


@dataclass
class HomeEntryResponse(DataClassJSONMixin):
    """Single home screen entry."""

    id: int
    type: str
    selection: Optional[HomeSelectionResponse] = None


@dataclass
class HomeEntriesResponse(DataClassJSONMixin):
    """Response from GET /discovery/v3/home_entries."""

    entries: list[HomeEntryResponse]


@dataclass
class SeriesResponse(DataClassJSONMixin):
    id: int
    type: str
    title: str
    description: str
    content_type: str
    authors: list[ShortAuthorResponse]
    narrators: list[ShortNarratorResponse]
    volumes: int
    avg_series_rating: float
    total_ratings: int
    cover_images: list[CoverImageResponse]
    show_filter: bool
    sort_fields: list[SortFieldResponse]
    categories: list[CategoryResponse]
    social_meta_info: SocialMetaInfoResponse


@dataclass
class SeriesPageResponse(DataClassJSONMixin):
    series: list[SeriesResponse]


@dataclass
class BookReadingResponse(DataClassJSONMixin):
    elapsed_time: Optional[int] = None
    page_number: Optional[int] = None
    path: Optional[str] = None
    idref: Optional[str] = None
    percentage: Optional[float] = None
    reached_at: Optional[datetime.datetime] = None


@dataclass
class UpdateBookReadingBodyRequest(DataClassJSONMixin):
    position: BookReadingResponse


@dataclass
class ProfileSettings(DataClassJSONMixin):
    global_format_filter: Optional[list[str]] = None
    global_language_filter: Optional[list[str]] = None
    profile_was_onboarded: Optional[bool] = None


@dataclass
class AvatarResponse(DataClassJSONMixin):
    id: int
    avatar: str
    avatar_thumbnail: str


@dataclass
class ProfileResponse(DataClassJSONMixin):
    id: int
    name: str
    login_key: str
    customer_id: int
    is_main: bool
    filter: str
    color_index: int
    settings: ProfileSettings
    is_magazine_enabled: bool
    surname: Optional[str] = None
    category: Optional[str] = None
    img_status: Optional[str] = None
    pic_url: Optional[str] = None
    bio: Optional[str] = None
    birth_year: Optional[int] = None
    avatar: Optional[AvatarResponse] = None


@dataclass
class ProfilesResponse(DataClassJSONMixin):
    profiles: list[ProfileResponse]
    max_profiles: int
    max_login_count: int
    colors: list[str]


@dataclass
class AccountSettings(DataClassJSONMixin):
    parental_control_pin: Optional[str] = None
    pincode_enabled: Optional[bool] = None


class TsSerializationStrategy(SerializationStrategy):
    def serialize(self, value: datetime.datetime) -> int:
        return int(value.timestamp() * 1000)

    def deserialize(self, value: int) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(value / 1000.0, tz=datetime.timezone.utc)


class UserType(enum.StrEnum):
    MEMBER = "MEMBER"
    NONMEMBER = "NONMEMBER"
    VISITOR = "VISITOR"


@dataclass
class AccountResponse(DataClassJSONMixin):
    id: int
    email: str
    country: str
    sign_in_count: int
    accept_newsletter: bool
    accept_push: bool
    emailable: bool
    user_type: UserType
    login_token: Optional[str] = None
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_sub_states: Optional[list[str]] = None
    settings: Optional[AccountSettings] = None
    referral_url: Optional[str] = None
    first_app_logged_in: Optional[datetime.datetime] = None
    channel: Optional[str] = None

    class Config:
        serialization_strategy = {
            datetime.datetime: TsSerializationStrategy(),
        }


@dataclass
class ProductsPageResponse(DataClassJSONMixin):
    products: list[ProductResponse]
    results_count: Optional[int] = None


@dataclass
class AutocompleteEntry(DataClassJSONMixin):
    text: str
    position: int


@dataclass
class AutocompleteResponse(DataClassJSONMixin):
    auto_complete: list[AutocompleteEntry] = field(default_factory=list[AutocompleteEntry])
    """Book matches"""
    auto_complete_mag: list[AutocompleteEntry] = field(default_factory=list[AutocompleteEntry])
    """Magazine matches"""
    did_you_mean: list[AutocompleteEntry] = field(default_factory=list[AutocompleteEntry])
    """Book suggestions"""
    did_you_mean_mag: list[AutocompleteEntry] = field(default_factory=list[AutocompleteEntry])
    """Magazine suggestions"""


@dataclass
class PersonResponse(DataClassJSONMixin):
    id: int
    show_filter: bool
    title: Optional[str] = None
    type: Optional[str] = None
    bio: Optional[str] = None
    count: Optional[int] = None
    image: Optional[str] = None
    social_meta_info: Optional[SocialMetaInfoResponse] = None
    sort_fields: list[SortFieldResponse] = field(default_factory=list[SortFieldResponse])


@dataclass
class DailyUsageDataResponse(DataClassJSONMixin):
    upddate: Optional[float] = None
    usage_time: Optional[float] = None


@dataclass
class ReadingTimeResponse(DataClassJSONMixin):
    month: int
    year: int
    total_reading_seconds_this_month: int
    total_reading_seconds_last_month: int
    daywise_readtime_in_seconds_this_month: list[DailyUsageDataResponse] = field(
        default_factory=list[DailyUsageDataResponse]
    )
    daywise_readtime_in_seconds_last_month: list[DailyUsageDataResponse] = field(
        default_factory=list[DailyUsageDataResponse]
    )


@dataclass
class ReadingTimeContainerResponse(DataClassJSONMixin):
    reading_time: ReadingTimeResponse

@dataclass
class ProfileTokenResponse(DataClassJSONMixin):
    profile_token: str