from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class TagStatus(Enum):
    UNTAGGED = auto()
    PARTIAL = auto()
    TAGGED = auto()


class ImageHandling(Enum):
    EMBED = "embed"
    SAVE = "save"
    BOTH = "both"
    NONE = "none"


class AuthMode(Enum):
    AUTO = "auto"
    TOKEN = "token"
    OAUTH = "oauth"
    KEY_SECRET = "key_secret"
    NONE = "none"


class TagMode(Enum):
    REPLACE = "replace"
    MERGE = "merge"


@dataclass(slots=True, frozen=True)
class TrackInfo:
    position: str
    title: str
    artists: list[str] = field(default_factory=list)
    side: str | None = None


@dataclass(slots=True, frozen=True)
class ImageInfo:
    uri: str
    type: str
    resource_url: str


@dataclass(slots=True, frozen=True)
class DiscogsRelease:
    id: int
    artists: list[str]
    title: str
    tracklist: list[TrackInfo]
    year: int | None = None
    released: str | None = None
    country: str | None = None
    label: str | None = None
    catno: str | None = None
    genres: list[str] = field(default_factory=list)
    styles: list[str] = field(default_factory=list)
    notes: str | None = None
    formats: list[str] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class AudioFile:
    path: Path
    extension: str
    tag_status: TagStatus = TagStatus.UNTAGGED
    sample_rate: int | None = None
    bit_depth: int | None = None
    duration: float | None = None


@dataclass(slots=True, frozen=True)
class AppConfig:
    library_root: Path
    recordings_root: Path | None = None
    consumer_key: str | None = None
    consumer_secret: str | None = None
    discogs_token: str | None = None
    discogs_secret: str | None = None
    auth_mode: AuthMode = AuthMode.AUTO
    tag_mode: TagMode = TagMode.REPLACE
    naming_pattern: str = "{artist}/{album} ({year})/{track_number} - {title}"
    image_handling: ImageHandling = ImageHandling.BOTH
    backup_enabled: bool = False
    backup_dir: Path | None = None
