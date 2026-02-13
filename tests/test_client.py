"""Tests for main client."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from nextory.client import NextoryClient


def _mock_session(*responses):
    """Create a mock session that returns responses in order."""
    session = MagicMock()
    side_effects = []
    for resp in responses:
        mock_resp = AsyncMock()
        if isinstance(resp, str):
            mock_resp.ok = True
            mock_resp.text = AsyncMock(return_value=resp)
        else:
            mock_resp.ok = resp.get("ok", True)
            mock_resp.text = AsyncMock(return_value=resp["text"])
            mock_resp.status = resp.get("status", 200)
            mock_resp.url = resp.get("url", "https://api.nextory.com/test")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=None)
        side_effects.append(cm)
    session.request = MagicMock(side_effect=side_effects)
    return session


@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client as async context manager."""
    async with NextoryClient(login_key="test_key") as client:
        assert client is not None
        session = client._get_session()
        assert session is not None


@pytest.mark.asyncio
async def test_client_with_provided_session():
    """Test client with provided session."""
    mock_session = MagicMock()
    client = NextoryClient(login_key="test_key", session=mock_session)
    assert client._session == mock_session
    assert client._own_session is False
    await client.close()


@pytest.mark.asyncio
async def test_auth_headers():
    """Test auth_headers property."""
    client = NextoryClient(
        login_token="lt", login_key="lk", profile_token="pt", country="SE",
    )
    h = client.auth_headers
    assert h["X-Login-Token"] == "lt"
    assert h["X-Profile-Token"] == "pt"
    assert h["X-Country-Code"] == "SE"
    assert "X-Application-Id" in h


@pytest.mark.asyncio
async def test_get_libraries():
    """Test getting library lists."""
    session = _mock_session(
        '{"product_lists": [{"id": "list_1", "name": "Want to Read", "offline_available": false, '
        '"editable": true, "deletable": false, "is_content_frozen": false, "type": "want_to_read", '
        '"created_date": "2024-01-01T00:00:00Z", "cover_images": [], "content_type": ["book"], '
        '"filters": [], "item_count": 5}], "lists": []}'
    )
    client = NextoryClient(login_key="k", session=session)
    library = await client.get_libraries()
    assert library.product_lists is not None
    assert len(library.product_lists) == 1
    assert library.product_lists[0].id == "list_1"


@pytest.mark.asyncio
async def test_get_product_details():
    """Test getting product details."""
    session = _mock_session(
        '{"id": 456, "title": "Test Audiobook", "media_type": "audiobook", "is_adult_book": false, '
        '"average_rating": 4.5, "number_of_rates": 100, "language": "en", '
        '"authors": [{"name": "Test Author", "id": 1}], '
        '"narrators": [{"name": "Test Narrator", "id": 2}], '
        '"formats": [{"identifier": 789, "type": "hls", "img_url": "https://example.com/cover.jpg", '
        '"publication_date": "2024-01-01", "publisher": {"name": "Test Publisher", "id": 10}, '
        '"cover_ratio": 1.5, "state": "available", "free": false, "purchased": true, '
        '"time_limited": false, "preview": false, "translators": [], "duration": 7200}], '
        '"profile_product": {"in_library": true, "is_completed": false, "is_ongoing": true}, '
        '"description_full": "A test audiobook"}'
    )
    client = NextoryClient(login_key="k", session=session)
    product = await client.get_product_details(456)
    assert product.id == 456
    assert product.title == "Test Audiobook"
    assert product.authors[0].name == "Test Author"


@pytest.mark.asyncio
async def test_get_audio_package():
    """Test getting audio package."""
    session = _mock_session(
        '{"duration": 3600, "files": [{"idref": "file_001", '
        '"uri": "https://example.com/audio/master.m3u8", '
        '"start_at": 0, "end_at": 60000, "duration": 60000, "title": "Chapter 1"}]}'
    )
    client = NextoryClient(login_key="k", session=session)
    pkg = await client.get_audio_package(789)
    assert pkg.duration == 3600
    assert len(pkg.files) == 1
    assert pkg.files[0].idref == "file_001"


@pytest.mark.asyncio
async def test_get_position():
    """Test getting reading position."""
    session = _mock_session(
        '{"percentage": 45.5, "reached_at": "2024-01-28T12:00:00Z", "elapsed_time": 1800}'
    )
    client = NextoryClient(login_key="k", session=session)
    pos = await client.get_position(789)
    assert pos.percentage == 45.5
    assert pos.elapsed_time == 1800


@pytest.mark.asyncio
async def test_patch_position():
    """Test updating reading position."""
    session = _mock_session("")
    client = NextoryClient(login_key="k", session=session)
    await client.patch_position(profile_id=123, format_id=789, percentage=50.0, elapsed_time=2000)
    session.request.assert_called_once()
    assert session.request.call_args[0][0] == "PATCH"


@pytest.mark.asyncio
async def test_expired_profile_token_retry():
    """Test that expired profile token triggers refresh and retry."""
    # First call: expired token error. Second call (retry after refresh): success.
    session = _mock_session(
        {"ok": False, "status": 401, "text": '{"error": {"code": 2002, "key": "expired", "message": "expired", "description": "token expired"}}'},
        '{"percentage": 10.0, "reached_at": "2024-01-01T00:00:00Z", "elapsed_time": 100}',
    )
    # _refresh_profile_token uses session.post directly
    mock_refresh_resp = AsyncMock()
    mock_refresh_resp.ok = True
    mock_refresh_resp.json = AsyncMock(return_value={"profile_token": "new_token"})
    refresh_cm = MagicMock()
    refresh_cm.__aenter__ = AsyncMock(return_value=mock_refresh_resp)
    refresh_cm.__aexit__ = AsyncMock(return_value=None)
    session.post = MagicMock(return_value=refresh_cm)

    client = NextoryClient(login_key="k", profile_token="old", session=session)
    pos = await client.get_position(789)
    assert pos.elapsed_time == 100
    assert client.profile_token == "new_token"
