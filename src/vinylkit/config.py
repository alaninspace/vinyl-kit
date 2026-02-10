from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from platformdirs import user_config_dir

from vinylkit.exceptions import ConfigError
from vinylkit.models import (
    AppConfig,
    AuthMode,
    DiscMapping,
    ImageHandling,
    TagMode,
    TrackNumbering,
)

APP_NAME = "vinylkit"


def get_config_path() -> Path:
    """Get the platform-appropriate path for the config file."""
    env_path = os.environ.get("VINYLKIT_CONFIG")
    if env_path:
        return Path(env_path)
    return Path(user_config_dir(APP_NAME)) / "config.toml"


def load_config() -> AppConfig:
    """
    Load configuration from the TOML file.
    Returns defaults if the file does not exist.
    """
    path = get_config_path()
    if not path.exists():
        # Return default config (must at least have a library root)
        return AppConfig(library_root=Path.cwd())

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise ConfigError(f"Failed to read config at {path}: {e}") from e

    return AppConfig(
        library_root=Path(data.get("library_root", Path.cwd())),
        recordings_root=Path(data["recordings_root"])
        if "recordings_root" in data
        else None,
        consumer_key=data.get("consumer_key"),
        consumer_secret=data.get("consumer_secret"),
        discogs_token=data.get("discogs_token"),
        discogs_secret=data.get("discogs_secret"),
        auth_mode=AuthMode(data.get("auth_mode", "auto")),
        tag_mode=TagMode(data.get("tag_mode", "replace")),
        track_numbering=TrackNumbering(data.get("track_numbering", "numeric")),
        disc_mapping=DiscMapping(data.get("disc_mapping", "physical")),
        naming_pattern=data.get(
            "naming_pattern", "{artist}/{year} - {album}/{track_number} - {title}"
        ),
        image_handling=ImageHandling(data.get("image_handling", "both")),
        collect_all_artwork=data.get("collect_all_artwork", False),
        artwork_subdir=data.get("artwork_subdir", "Artwork"),
        backup_enabled=data.get("backup_enabled", False),
        backup_dir=Path(data["backup_dir"]) if "backup_dir" in data else None,
        info_filename=data.get("info_filename", "release_info.txt"),
        artwork_filename=data.get("artwork_filename", "folder.jpg"),
        search_page_size=data.get("search_page_size", 5),
        default_format=data.get("default_format", ["Vinyl"]),
        auto_move=data.get("auto_move", False),
        delete_after_migration=data.get("delete_after_migration", False),
        replace_artwork_on_migration=data.get("replace_artwork_on_migration", True),
    )


def save_config(config: AppConfig) -> None:
    """Save the configuration to the TOML file."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {
        "library_root": str(config.library_root),
        "auth_mode": config.auth_mode.value,
        "tag_mode": config.tag_mode.value,
        "track_numbering": config.track_numbering.value,
        "disc_mapping": config.disc_mapping.value,
        "naming_pattern": config.naming_pattern,
        "image_handling": config.image_handling.value,
        "collect_all_artwork": config.collect_all_artwork,
        "artwork_subdir": config.artwork_subdir,
        "backup_enabled": config.backup_enabled,
        "info_filename": config.info_filename,
        "artwork_filename": config.artwork_filename,
        "search_page_size": config.search_page_size,
        "default_format": config.default_format,
        "auto_move": config.auto_move,
        "delete_after_migration": config.delete_after_migration,
        "replace_artwork_on_migration": config.replace_artwork_on_migration,
    }
    if config.consumer_key:
        data["consumer_key"] = config.consumer_key
    if config.consumer_secret:
        data["consumer_secret"] = config.consumer_secret
    if config.recordings_root:
        data["recordings_root"] = str(config.recordings_root)
    if config.discogs_token:
        data["discogs_token"] = config.discogs_token
    if config.discogs_secret:
        data["discogs_secret"] = config.discogs_secret
    if config.backup_dir:
        data["backup_dir"] = str(config.backup_dir)

    try:
        with path.open("wb") as f:
            tomli_w.dump(data, f)
    except Exception as e:
        raise ConfigError(f"Failed to write config at {path}: {e}") from e
