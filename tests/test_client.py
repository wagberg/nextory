"""Tests for main client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nextory.client import NextoryClient


@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client as async context manager."""
    async with NextoryClient(
        username="test@example.com", password="password", login_key="test_key"
    ) as client:
        assert client is not None
        # Session is created lazily on first use
        session = client._get_session()
        assert session is not None


@pytest.mark.asyncio
async def test_client_with_provided_session():
    """Test client with provided session."""
    mock_session = MagicMock()
    client = NextoryClient(
        username="test@example.com",
        password="password",
        login_key="test_key",
        session=mock_session,
    )

    assert client._session == mock_session
    assert client._own_session is False

    # Should not close provided session
    await client.close()


@pytest.mark.asyncio
async def test_get_library():
    """Test getting library lists."""
    mock_session = MagicMock()

    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value='{"product_lists": [{"id": "list_1", "name": "Want to Read", "offline_available": false, "editable": true, "deletable": false, "is_content_frozen": false, "type": "want_to_read", "created_date": "2024-01-01T00:00:00Z", "cover_images": [], "content_type": ["book"], "filters": [], "item_count": 5}], "lists": null}')

    # Mock the get method to return a proper async context manager
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock(return_value=mock_cm)

    client = NextoryClient(
        username="test@example.com",
        password="password",
        login_key="test_key",
        session=mock_session,
    )

    library = await client.get_libraries()

    assert library.product_lists is not None
    assert len(library.product_lists) == 1
    assert library.product_lists[0].id == "list_1"
    assert library.product_lists[0].name == "Want to Read"
    assert library.product_lists[0].type == "want_to_read"
    assert library.product_lists[0].item_count == 5


@pytest.mark.asyncio
async def test_get_product_details(sample_product_response_data):
    """Test getting product details."""
    mock_session = MagicMock()

    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value='{"id": 456, "title": "Test Audiobook", "media_type": "audiobook", "is_adult_book": false, "average_rating": 4.5, "number_of_rates": 100, "language": "en", "authors": [{"name": "Test Author", "id": 1}], "narrators": [{"name": "Test Narrator", "id": 2}], "formats": [{"identifier": 789, "type": "hls", "img_url": "https://example.com/cover.jpg", "publication_date": "2024-01-01", "publisher": {"name": "Test Publisher", "id": 10}, "cover_ratio": 1.5, "state": "available", "free": false, "purchased": true, "time_limited": false, "preview": false, "translators": [], "duration": 7200}], "profile_product": {"in_library": true, "is_completed": false, "is_ongoing": true}, "description_full": "A test audiobook"}')

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock(return_value=mock_cm)

    client = NextoryClient(
        username="test@example.com",
        password="password",
        login_key="test_key",
        session=mock_session,
    )

    product = await client.get_product_details(456)

    assert product.id == 456
    assert product.title == "Test Audiobook"
    assert len(product.authors) == 1
    assert product.authors[0].name == "Test Author"


@pytest.mark.asyncio
async def test_get_audio_package(sample_audio_package_data):
    """Test getting audio package."""
    mock_session = MagicMock()

    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value='{"duration": 3600, "files": [{"idref": "file_001", "uri": "https://example.com/audio/master.m3u8", "start_at": 0, "end_at": 60000, "duration": 60000, "title": "Chapter 1"}]}')

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock(return_value=mock_cm)

    client = NextoryClient(
        username="test@example.com",
        password="password",
        login_key="test_key",
        session=mock_session,
    )

    audio_package = await client.get_audio_package(789)

    assert audio_package.duration == 3600
    assert len(audio_package.files) == 1
    assert audio_package.files[0].idref == "file_001"


@pytest.mark.asyncio
async def test_get_position(sample_book_reading_response_data):
    """Test getting reading position."""
    mock_session = MagicMock()

    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value='{"percentage": 45.5, "reached_at": "2024-01-28T12:00:00Z", "elapsed_time": 1800}')

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock(return_value=mock_cm)

    client = NextoryClient(
        username="test@example.com",
        password="password",
        login_key="test_key",
        session=mock_session,
    )

    position = await client.get_position(789)

    assert position.percentage == 45.5
    assert position.elapsed_time == 1800


@pytest.mark.asyncio
async def test_patch_position():
    """Test updating reading position."""
    mock_session = MagicMock()

    mock_response = AsyncMock()

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.patch = MagicMock(return_value=mock_cm)

    client = NextoryClient(
        username="test@example.com",
        password="password",
        login_key="test_key",
        session=mock_session,
    )

    await client.patch_position(
        profile_id=123, format_id=789, percentage=50.0, elapsed_time=2000
    )

    mock_session.patch.assert_called_once()


@pytest.mark.asyncio
async def test_middleware_integration():
    """Test that middlewares are properly configured."""
    mock_session = MagicMock()

    client = NextoryClient(
        username="test@example.com",
        password="password",
        login_key="test_key",
        login_token="test_login_token",
        profile_token="test_profile_token",
        session=mock_session,
    )

    # Verify middlewares are configured
    assert len(client._middlewares) == 3
    assert client._middlewares[0].__class__.__name__ == "NextoryLoginMiddleware"
    assert client._middlewares[1].__class__.__name__ == "NextoryProfileMiddleware"
    assert client._middlewares[2].__class__.__name__ == "NextoryErrorMiddleware"

    # Verify tokens are set
    assert client._middlewares[0]._login_token == "test_login_token"
    assert client._middlewares[1]._profile_token == "test_profile_token"

