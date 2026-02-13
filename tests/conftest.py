"""Pytest configuration."""

import typing as t

import pytest


@pytest.fixture
def sample_audio_package_data() -> dict[str, t.Any]:
    """Sample audio package data for testing."""
    return {
        "duration": 3600,
        "files": [
            {
                "idref": "file_001",
                "uri": "https://example.com/audio/master.m3u8",
                "start_at": 0,
                "end_at": 60000,
                "duration": 60000,
                "title": "Chapter 1",
            }
        ],
    }


@pytest.fixture
def sample_product_response_data() -> dict[str, t.Any]:
    """Sample product response data for testing."""
    return {
        "id": 456,
        "title": "Test Audiobook",
        "media_type": "audiobook",
        "is_adult_book": False,
        "average_rating": 4.5,
        "number_of_rates": 100,
        "language": "en",
        "authors": [{"name": "Test Author", "id": 1}],
        "narrators": [{"name": "Test Narrator", "id": 2}],
        "formats": [
            {
                "identifier": 789,
                "type": "hls",
                "img_url": "https://example.com/cover.jpg",
                "publication_date": "2024-01-01",
                "publisher": {"name": "Test Publisher", "id": 10},
                "cover_ratio": 1.5,
                "state": "available",
                "free": False,
                "purchased": True,
                "time_limited": False,
                "preview": False,
                "translators": [],
                "duration": 7200,
            }
        ],
        "profile_product": {
            "in_library": True,
            "is_completed": False,
            "is_ongoing": True,
        },
        "description_full": "A test audiobook",
    }


@pytest.fixture
def sample_book_reading_response_data() -> dict[str, t.Any]:
    """Sample book reading response data for testing."""
    return {
        "percentage": 45.5,
        "reached_at": "2024-01-28T12:00:00Z",
        "elapsed_time": 1800,
    }


@pytest.fixture
def sample_profiles_response_data() -> dict[str, t.Any]:
    """Sample profiles response data for testing."""
    return {
        "profiles": [
            {
                "id": 123,
                "name": "Test",
                "surname": "Profile",
                "login_key": "test_key_123",
                "customer_id": 1,
                "is_main": True,
                "filter": "all",
                "color_index": 0,
                "settings": {},
                "is_magazine_enabled": False,
            }
        ],
        "max_profiles": 5,
        "max_login_count": 3,
        "colors": ["#FF0000", "#00FF00"],
    }
