"""Tests for configuration management."""

import json
import random
import string
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from nextory.config import ProfileConfig


@pytest.fixture
def temp_config_dir(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    """Create temporary config directory."""
    config_dir = tmp_path / ".config" / "nextory"
    config_dir.mkdir(parents=True)

    # Patch the get_config_path method to use temp directory
    def mock_get_config_path():
        return config_dir / "profile.json"

    monkeypatch.setattr(ProfileConfig, "get_config_path", staticmethod(mock_get_config_path))
    return config_dir


@pytest.fixture
def login_token() -> str:
    """Generate a random login key for testing."""
    return "".join(random.choices(string.ascii_letters + string.digits + "+/", k=64))


@pytest.fixture
def login_key() -> str:
    """Generate a random login key for testing."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=32))


@pytest.fixture
def profile_token() -> str:
    """Generate a random profile key for testing."""
    return "".join(random.choices(string.ascii_letters + string.digits + "+/", k=64))


def test_profile_config_save(
    temp_config_dir: Path, login_token: str, login_key: str, profile_token: str
):
    """Test saving profile configuration."""
    config = ProfileConfig(login_token=login_token, login_key=login_key, profile_token=profile_token)
    config.save()

    config_path = ProfileConfig.get_config_path()
    assert config_path.exists()

    with open(config_path) as f:
        data = json.load(f)
        assert data["login_token"] == login_token
        assert data["login_key"] == login_key
        assert data["profile_token"] == profile_token


def test_profile_config_load(
    temp_config_dir: Path, login_token: str, login_key: str, profile_token: str
):
    """Test loading profile configuration."""
    config_path = ProfileConfig.get_config_path()
    config_data = {
        "login_token": login_token,
        "login_key": login_key,
        "profile_token": profile_token,
    }

    with open(config_path, "w") as f:
        json.dump(config_data, f)

    config = ProfileConfig.load()
    assert config is not None
    assert config.login_token == login_token
    assert config.login_key == login_key
    assert config.profile_token == profile_token


def test_profile_config_load_nonexistent(temp_config_dir: Path):
    """Test loading when config file doesn't exist."""
    config = ProfileConfig.load()
    assert config is None


def test_profile_config_save_and_load(
    temp_config_dir: Path, login_token: str, login_key: str, profile_token: str
):
    """Test save and load roundtrip."""
    original_config = ProfileConfig(
        login_token=login_token, login_key=login_key, profile_token=profile_token
    )
    original_config.save()

    loaded_config = ProfileConfig.load()
    assert loaded_config is not None
    assert loaded_config.login_token == original_config.login_token
    assert loaded_config.login_key == original_config.login_key
    assert loaded_config.profile_token == original_config.profile_token
