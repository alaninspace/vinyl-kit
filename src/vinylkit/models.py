from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


class TrackNumbering(Enum):
    NUMERIC = "numeric"  # 1, 2, 3...
    ORIGINAL = "original"  # A1, B1...
    PER_SIDE = "per_side"  # 1, 2, 1, 2...


class DiscMapping(Enum):
    SINGLE = "single"  # All on Disc 1
    PER_SIDE = "per_side"  # Side A=1, B=2...
    PHYSICAL = "physical"  # A,B=1, C,D=2... (Standard Vinyl)
    ORIGINAL = "original"  # Uses Discogs physical count


@dataclass(slots=True, frozen=True)
class TrackInfo:
    position: str
    title: str
    artists: list[str] = field(default_factory=list)
    side: str | None = None
    extraartists: list[ExtraArtistInfo] = field(default_factory=list)
    duration: str | None = None


@dataclass(slots=True, frozen=True)
class ImageInfo:
    uri: str
    type: str
    resource_url: str


@dataclass(slots=True, frozen=True)
class LabelInfo:
    name: str
    catno: str | None = None


@dataclass(slots=True, frozen=True)
class CompanyInfo:
    name: str
    entity_type_name: str


@dataclass(slots=True, frozen=True)
class FormatInfo:
    name: str
    qty: str
    descriptions: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class IdentifierInfo:
    type: str
    value: str
    description: str | None = None


@dataclass(slots=True, frozen=True)
class ExtraArtistInfo:
    name: str
    role: str


@dataclass(slots=True, frozen=True)
class DiscogsRelease:
    id: int
    artists: list[str]
    title: str
    tracklist: list[TrackInfo]
    year: int | None = None
    released: str | None = None
    country: str | None = None
    label: str | None = None  # Primary label name
    catno: str | None = None  # Primary catno
    labels: list[LabelInfo] = field(default_factory=list)
    companies: list[CompanyInfo] = field(default_factory=list)
    formats: list[FormatInfo] = field(default_factory=list)
    identifiers: list[IdentifierInfo] = field(default_factory=list)
    extraartists: list[ExtraArtistInfo] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    styles: list[str] = field(default_factory=list)
    notes: str | None = None
    images: list[ImageInfo] = field(default_factory=list)
    uri: str | None = None
    master_id: int | None = None
    master_url: str | None = None
    artists_sort: str | None = None
    data_quality: str | None = None
    format_quantity: int | None = None


@dataclass(slots=True, frozen=True)
class AudioFile:
    path: Path
    extension: str
    tag_status: TagStatus = TagStatus.UNTAGGED
    sample_rate: int | None = None
    bit_depth: int | None = None
    duration: float | None = None


@dataclass(slots=True)
class RateLimitInfo:
    """Live rate limit telemetry updated on every API response.

    Intentionally mutable (not frozen) since fields are updated in-place.
    """

    limit: int | None = None  # X-Discogs-Ratelimit
    used: int | None = None  # X-Discogs-Ratelimit-Used
    remaining: int | None = None  # X-Discogs-Ratelimit-Remaining
    last_updated: float = 0.0
    peak_used: int = 0  # High-water mark


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
    track_numbering: TrackNumbering = TrackNumbering.NUMERIC
    disc_mapping: DiscMapping = DiscMapping.PHYSICAL
    naming_pattern: str = "{artist}/{year} - {album}/{track_number} - {title}"
    image_handling: ImageHandling = ImageHandling.BOTH
    collect_all_artwork: bool = False
    artwork_subdir: str = "Artwork"
    backup_enabled: bool = False
    backup_dir: Path | None = None
    info_filename: str = "release_info.txt"
    artwork_filename: str = "folder.jpg"
    search_page_size: int = 5
    default_format: list[str] = field(default_factory=lambda: ["Vinyl"])
    auto_move: bool = False
    delete_after_migration: bool = False
    replace_artwork_on_migration: bool = True
    replace_tags_on_migration: bool = True
    skip_tags: list[str] = field(default_factory=list)
    cache_enabled: bool = True
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file: Path | None = None
    log_rotation: str = "5 MB"
    log_retention: int = 5
