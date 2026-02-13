"""Tests for data models."""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
import datetime

from nextory.models import (
    AccountResponse,
    ApiErrorResponse,
    Audiobook,
    AudioFile,
    AudioPackage,
    NetworkErrorResponse,
    NextoryApiErrorResponse,
    Profile,
    ReadingPosition,
    UsageBlock,
    UserType,
)


def test_account_serialization():
    test_account_data = '''
    {
        "id": 894651,
        "email": "name@example.com",
        "country": "GB",
        "sign_in_count": 24,
        "accept_newsletter": true,
        "accept_push": true,
        "emailable": true,
        "user_type": "MEMBER",
        "login_token": null,
        "phone_number": "1234567890",
        "first_name": "John",
        "last_name": "Doe",
        "user_sub_states": [],
        "settings": {
            "parental_control_pin": "0000",
            "pincode_enabled": true
        },
        "referral_url": "https://www.nextory.com/",
        "first_app_logged_in": 946684800000,
        "channel": "WEB"
    }'''

    account = AccountResponse.from_json(test_account_data)
    assert account.id == 894651
    assert account.email == "name@example.com"
    assert account.first_name == "John"
    assert account.last_name == "Doe"
    assert account.user_type is UserType.MEMBER
    assert account.settings is not None
    assert account.settings.parental_control_pin == "0000"
    assert account.settings.pincode_enabled
    assert account.first_app_logged_in == datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

def test_profile_serialization():
    """Test Profile model serialization."""
    sample_profile_data = {
        "id": 123,
        "name": "Test Profile",
        "login_key": "test_key_123",
        "is_main": True,
    }
    profile = Profile.from_dict(sample_profile_data)
    assert profile.id == 123
    assert profile.name == "Test Profile"
    assert profile.login_key == "test_key_123"
    assert profile.is_main is True
    assert profile.to_dict() == sample_profile_data


# def test_audio_file_serialization():
#     """Test AudioFile model serialization."""
#     sample_audio_file_data = {
#         "idref": "file_001",
#         "uri": "https://example.com/audio/master.m3u8",
#         "start_at": 0,
#         "end_at": 60000,
#         "duration": 60000,
#         "title": "Chapter 1",
#     }
#     audio_file = AudioFile.from_dict(sample_audio_file_data)
#     assert audio_file.idref == "file_001"
#     assert audio_file.uri == "https://example.com/audio/master.m3u8"
#     assert audio_file.start_at == 0
#     assert audio_file.end_at == 60000
#     assert audio_file.duration == 60000
#     assert audio_file.title == "Chapter 1"
#     assert audio_file.to_dict() == sample_audio_file_data


def test_audio_package_serialization():
    """Test AudioPackage model serialization."""
    sample_audio_file_data = {
        "idref": "file_001",
        "uri": "https://example.com/audio/master.m3u8",
        "start_at": 0,
        "end_at": 60000,
        "duration": 60000,
        "title": "Chapter 1",
    }
    sample_audio_package_data = {"duration": 3600, "files": [sample_audio_file_data]}
    audio_package = AudioPackage.from_dict(sample_audio_package_data)
    assert audio_package.duration == 3600
    assert len(audio_package.files) == 1
    assert audio_package.files[0].idref == "file_001"


def test_audiobook_serialization():
    """Test Audiobook model serialization."""
    sample_audiobook_data = {
        "id": 456,
        "title": "Test Audiobook",
        "authors": [{"name": "Test Author", "id": 1}],
        "narrators": [{"name": "Test Narrator", "id": 2}],
        "formats": [{"type": "hls", "identifier": 789, "img_url": "https://example.com/cover.jpg"}],
        "description_full": "A test audiobook",
        "duration": 7200,
    }
    audiobook = Audiobook.from_dict(sample_audiobook_data)
    assert audiobook.id == 456
    assert audiobook.title == "Test Audiobook"
    assert len(audiobook.authors) == 1
    assert audiobook.authors[0].name == "Test Author"
    assert len(audiobook.narrators) == 1
    assert audiobook.narrators[0].name == "Test Narrator"
    assert len(audiobook.formats) == 1
    assert audiobook.formats[0].type == "hls"
    assert audiobook.duration == 7200


def test_reading_position_serialization():
    """Test ReadingPosition model serialization."""
    sample_reading_position_data = {
        "percentage": 45.5,
        "reached_at": "2024-01-28T12:00:00Z",
        "elapsed_time": 1800,
    }
    position = ReadingPosition.from_dict(sample_reading_position_data)
    assert position.percentage == 45.5
    assert position.reached_at == "2024-01-28T12:00:00Z"
    assert position.elapsed_time == 1800


def test_usage_block_creation():
    """Test UsageBlock model creation."""
    usage_block = UsageBlock(
        format_type="hls",
        start_percentage=0.0,
        end_percentage=10.0,
        start_time=1000,
        end_time=2000,
        player_speed=1.0,
    )
    assert usage_block.format_type == "hls"
    assert usage_block.start_percentage == 0.0
    assert usage_block.end_percentage == 10.0
    assert usage_block.start_time == 1000
    assert usage_block.end_time == 2000
    assert usage_block.player_speed == 1.0


def test_audio_file_optional_fields():
    """Test AudioFile with optional fields."""
    minimal_data = {
        "idref": "file_002",
        "uri": "https://example.com/audio.mp3",
        "start_at": 0,
        "end_at": 30000,
        "duration": 30000,
    }
    audio_file = AudioFile.from_dict(minimal_data)
    assert audio_file.title is None
    # Mashumaro includes None fields in serialization
    result = audio_file.to_dict()
    assert result["idref"] == minimal_data["idref"]
    assert result["uri"] == minimal_data["uri"]
    assert result["duration"] == minimal_data["duration"]


def test_library_list_serialization():
    """Test LibraryList model serialization."""
    from nextory.models import LibraryList

    list_data = {
        "id": "list_1",
        "name": "Want to Read",
        "offline_available": False,
        "editable": True,
        "deletable": False,
        "is_content_frozen": False,
        "type": "want_to_read",
        "created_date": "2024-01-01T00:00:00Z",
        "cover_images": ["https://example.com/cover1.jpg"],
        "content_type": ["book"],
        "filters": [],
        "item_count": 5,
    }
    library_list = LibraryList.from_dict(list_data)
    assert library_list.id == "list_1"
    assert library_list.name == "Want to Read"
    assert library_list.type == "want_to_read"
    assert library_list.item_count == 5
    assert library_list.editable is True


def test_library_lists_serialization():
    """Test LibraryLists model serialization."""
    from nextory.models import LibraryLists

    lists_data = {
        "product_lists": [
            {
                "id": "list_1",
                "offline_available": False,
                "editable": True,
                "deletable": False,
                "is_content_frozen": False,
                "type": "want_to_read",
                "created_date": "2024-01-01T00:00:00Z",
                "cover_images": [],
                "content_type": ["book"],
                "filters": [],
            }
        ],
        "lists": None,
    }
    library_lists = LibraryLists.from_dict(lists_data)
    assert library_lists.product_lists is not None
    assert len(library_lists.product_lists) == 1
    assert library_lists.lists is None

def test_network_error_response():
    """Test NetworkErrorResponse deserialization."""
    sample_data = {
        "timestamp": "2026-01-29T10:25:42.751+00:00",
        "status": 400,
        "error": "Bad Request",
        "path": "/library/v1/me/library"
    }
    parsed = NetworkErrorResponse.from_dict(sample_data)
    assert isinstance(parsed, NetworkErrorResponse)
    assert parsed.status == 400
    assert parsed.error == "Bad Request"
    assert parsed.path == "/library/v1/me/library"

def test_network_error_response_discriminator():
    """Test NetworkErrorResponse discriminator from parent class."""
    sample_data = {
        "timestamp": "2026-01-29T10:25:42.751+00:00",
        "status": 400,
        "error": "Bad Request",
        "path": "/library/v1/me/library"
    }
    parsed = ApiErrorResponse.from_dict(sample_data)
    assert isinstance(parsed, NetworkErrorResponse)
    assert parsed.status == 400
    assert parsed.error == "Bad Request"
    assert parsed.path == "/library/v1/me/library"


def test_nextory_api_error_response():
    """Test NextoryApiErrorResponse deserialization."""
    sample_data = {
        "error": {
            "code": 2001,
            "key": "expired_login_token",
            "message": "Login token expired",
            "description": "The login token has expired"
        }
    }
    parsed = NextoryApiErrorResponse.from_dict(sample_data)
    assert isinstance(parsed, NextoryApiErrorResponse)
    assert parsed.error.code == 2001
    assert parsed.error.key == "expired_login_token"
    assert parsed.error.message == "Login token expired"
    assert parsed.error.description == "The login token has expired"

def test_nextory_api_error_response_discriminator():
    """Test NextoryApiErrorResponse discriminator from parent class."""
    sample_data = {
        "error": {
            "code": 2001,
            "key": "expired_login_token",
            "message": "Login token expired",
            "description": "The login token has expired"
        }
    }
    parsed = ApiErrorResponse.from_dict(sample_data)
    assert isinstance(parsed, NextoryApiErrorResponse)
    assert parsed.error.code == 2001
    assert parsed.error.key == "expired_login_token"
    assert parsed.error.message == "Login token expired"
    assert parsed.error.description == "The login token has expired"