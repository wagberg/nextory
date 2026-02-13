"""Configuration management for Nextory profiles."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from mashumaro.mixins.json import DataClassJSONMixin


@dataclass
class ProfileConfig(DataClassJSONMixin):
    """Profile configuration for saved profile."""
    login_token: str
    login_key: str
    profile_token: str

    @classmethod
    def get_config_path(cls) -> Path:
        """Get path to config file."""
        config_dir = Path.home() / ".config" / "nextory"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "profile.yaml"

    def save(self) -> None:
        """Save profile configuration to file."""
        config_path = self.get_config_path()
        with open(config_path, "w") as f:
            f.write(str(self.to_json()))

    @classmethod
    def load(cls) -> Optional["ProfileConfig"]:
        """Load profile configuration from file."""
        config_path = cls.get_config_path()
        if not config_path.exists():
            return None
        with open(config_path) as f:
            return cls.from_json(f.read())
