"""Shared helpers, constants, and re-exported dependencies for CLI commands.

Command modules access mockable external dependencies through this module
(e.g. ``_helpers.tag_audio_file``) so that a single mock-patch target
(``vinylkit.commands._helpers.X``) covers every consumer.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import rich_click as click
from loguru import logger
from rich.console import Console

from vinylkit.discogs import (
    DiscogsClient,
    describe_throttle_strategy,
    get_cache_dir,
)
from vinylkit.exceptions import DiscogsAPIError
from vinylkit.models import AppConfig, ImageHandling
from vinylkit.naming import generate_path, move_directory, move_file
from vinylkit.tagging import (
    calculate_track_and_disc,
    clear_audio_tags,
    get_track_number,
    save_artwork,
    scan_folder,
    tag_audio_file,
    write_release_info,
)
from vinylkit.utils import backup_file, natural_sort_key

if TYPE_CHECKING:
    from pathlib import Path

    from vinylkit.models import DiscogsRelease

# Suppress unused-import warnings — these names are accessed by command
# modules via ``_helpers.X`` so that tests can mock them in one place.
__all__ = [
    "DiscogsClient",
    "FolderSearchQuery",
    "backup_file",
    "calculate_track_and_disc",
    "clear_audio_tags",
    "describe_throttle_strategy",
    "extract_id",
    "generate_path",
    "get_cache_dir",
    "get_track_number",
    "is_low_quality_text_match",
    "move_directory",
    "move_file",
    "parse_folder_search_query",
    "save_artwork",
    "scan_folder",
    "tag_audio_file",
    "write_release_info",
]

# Shared Rich console
console = Console()

# Default Discogs API credentials
DEFAULT_CONSUMER_KEY = "placeholder_key"
DEFAULT_CONSUMER_SECRET = "placeholder_secret"


def get_client(config: AppConfig) -> DiscogsClient:
    """Initialise a :class:`DiscogsClient` with appropriate credentials."""
    key = config.consumer_key or DEFAULT_CONSUMER_KEY
    secret = config.consumer_secret or DEFAULT_CONSUMER_SECRET
    return DiscogsClient(
        key,
        secret,
        config.discogs_token,
        config.discogs_secret,
        cache_enabled=config.cache_enabled,
        auth_mode=config.auth_mode,
        normalize_discogs_duplicates=config.normalize_discogs_duplicates,
        anv_handling=config.anv_handling,
        position_overrides=config.position_overrides,
    )


def extract_id(folder_name: str) -> int | None:
    """Extract Discogs ID from a folder name.

    Supports three patterns:
    - Bracket suffix: ``Artist - Album [12345]`` -> ``12345``
    - Bare numeric: ``67890`` -> ``67890``
    - URL-style prefix: ``50224-Breeder-New-York-FM`` -> ``50224``
    """
    match = re.search(r"\[(\d+)\]$", folder_name)
    if match:
        return int(match.group(1)) or None
    if folder_name.strip().isdigit():
        return int(folder_name.strip()) or None
    match = re.match(r"^(\d+)-", folder_name.strip())
    if match:
        return int(match.group(1)) or None
    return None


_STANDALONE_WORDS = {
    "remix",
    "remixes",
    "mix",
    "mixes",
    "edit",
    "ep",
    "lp",
    "single",
    "cd",
    "flac",
    "mp3",
    "vinyl",
    "various",
}


@dataclass(slots=True, frozen=True)
class FolderSearchQuery:
    """Structured query details parsed from a folder name for Discogs API search."""

    catno: str | None
    cleaned_query: str
    raw_query: str


def parse_folder_search_query(folder_name: str) -> FolderSearchQuery:
    """Parse folder name into structured search queries for Discogs API.

    Extracts potential catalog numbers (trailing parens, brackets, scene-style,
    or prefix) and cleans artist/title text (converting '_And_' to '&').
    """
    catno: str | None = None
    m_cat: re.Match[str] | None = None

    # 1. Trailing parens: -(CATNO) or (CATNO)
    m = re.search(r"[-_\s]*\(([^)]+)\)\s*$", folder_name)
    if m:
        raw_cat = m.group(1).strip()
        if raw_cat.lower() not in _STANDALONE_WORDS:
            catno = raw_cat
            m_cat = m

    # 2. Square brackets: -[CATNO]- or [CATNO]
    if not catno:
        m = re.search(r"\[([^\]]+)\]", folder_name)
        if m:
            catno = m.group(1).strip()
            m_cat = m

    # 3. Scene style format: -Vinyl-(CATNO)-FLAC-Year or -Vinyl-CATNO-FLAC-Year
    if not catno:
        m = re.search(
            r"-(?:Vinyl|FLAC|MP3|CD)-([^-]+)-(?:Vinyl|FLAC|MP3|CD|\d{4})",
            folder_name,
            re.IGNORECASE,
        )
        if m:
            catno = m.group(1).strip()
            m_cat = m

    # 4. Front catno e.g. SUBBASE 28R - 1993 - DJ Hype...
    if not catno:
        m = re.match(
            r"^\s*([A-Za-z0-9_-]{3,15})\s*-\s*(?:\d{4}\b|[A-Za-z])", folder_name
        )
        if m:
            candidate = m.group(1).strip()
            if candidate.lower() not in _STANDALONE_WORDS and any(
                c.isdigit() for c in candidate
            ):
                catno = candidate
                m_cat = m

    # Clean catno (replacing underscores with spaces if any)
    catno_clean = catno.replace("_", " ").strip() if catno else None

    # Clean artist & title: strip out trailing catno parens/brackets/scene tags
    cleaned_base = folder_name
    if m_cat:
        cleaned_base = folder_name[: m_cat.start()].strip(" -_")

    # Convert _And_ to &
    cleaned_base = re.sub(r"[\s_-]+[A|a][N|n][D|d][\s_-]+", " & ", cleaned_base)
    # Remove underscores, hyphens, parentheses, and multiple spaces
    cleaned_artist_title = re.sub(r"[\._\-\(\)]+", " ", cleaned_base)
    cleaned_artist_title = re.sub(r"\s+", " ", cleaned_artist_title).strip()

    # Raw clean fallback (existing vinylkit behavior)
    raw_clean = (
        folder_name.replace("_", " ")
        .replace("-", " ")
        .replace("(", " ")
        .replace(")", " ")
        .strip()
    )
    raw_clean = re.sub(r"\s+", " ", raw_clean)

    return FolderSearchQuery(
        catno=catno_clean,
        cleaned_query=cleaned_artist_title,
        raw_query=raw_clean,
    )


def is_low_quality_text_match(
    results: list[dict[str, Any]], folder_query: FolderSearchQuery
) -> bool:
    """Check if Tier 1 text search returned low-quality compilation noise."""
    if not results or not folder_query.catno:
        return False
    top = results[0]
    title_raw = str(top.get("title", "")).lower()
    res_artist = title_raw.split("-", 1)[0].strip() if "-" in title_raw else title_raw

    q_words = [
        w.lower()
        for w in re.sub(r"[^\w\s]+", " ", folder_query.cleaned_query).split()
        if len(w) > 2
    ]
    if not q_words:
        return False

    first_q_word = q_words[0]
    if first_q_word != "various" and res_artist == "various":
        return True

    return first_q_word not in title_raw


@functools.lru_cache(maxsize=32)
def collect_audio_files(path: Path, natural_sort: bool = True) -> list[Path]:
    """Collect and sort supported audio files.

    LRU cache is used to avoid redundant network directory scans during
    a single command execution.
    """
    files = [
        p
        for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in (".mp3", ".flac")
    ]
    if natural_sort:
        return sorted(files, key=natural_sort_key)
    return sorted(files)


def display_relative(path: Path, root: Path) -> Path:
    """Return *path* relative to *root*, or the full path if not under it."""
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def check_collisions(
    moves: list[tuple[Path, Path]], dir_moves: list[tuple[Path, Path]]
) -> bool:
    """Check if any destination files or directories already exist.

    Returns ``True`` if it is safe to proceed (no collisions or user
    confirmed).
    """
    collisions: list[Path] = []
    for src, dst in moves:
        if src != dst and dst.exists():
            collisions.append(dst)

    for src, dst in dir_moves:
        if src != dst and dst.exists():
            collisions.append(dst)

    if not collisions:
        return True

    console.print(
        f"\n[bold yellow]Warning: {len(collisions)} destination"
        " file(s)/folder(s) already exist:[/bold yellow]"
    )
    for c in collisions[:10]:
        console.print(f"  [yellow]! {c}[/yellow]")
    if len(collisions) > 10:
        console.print(f"  [yellow]... and {len(collisions) - 10} more[/yellow]")

    return click.confirm("\nOverwrite existing files/folders?", default=False)


def plan_supplementary_moves(
    path: Path,
    target_dir: Path,
    lib_root: Path,
    config: AppConfig,
    moves: list[tuple[Path, Path]],
) -> list[tuple[Path, Path]]:
    """Plan moves for info files, artwork files, and artwork subdirs.

    Returns a list of directory moves (artwork subdirs).
    """
    dir_moves: list[tuple[Path, Path]] = []

    # Info file
    info_file = path / config.info_filename
    if info_file.exists():
        info_target = target_dir / config.info_filename
        if info_file != info_target:
            moves.append((info_file, info_target))
            rel = display_relative(info_target, lib_root)
            console.print(f"[cyan]{info_file.name}[/cyan] -> [green]{rel}[/green]")

    # Artwork file
    artwork_file = path / config.artwork_filename
    if artwork_file.exists():
        artwork_target = target_dir / config.artwork_filename
        if artwork_file != artwork_target:
            moves.append((artwork_file, artwork_target))
            rel = display_relative(artwork_target, lib_root)
            console.print(f"[cyan]{artwork_file.name}[/cyan] -> [green]{rel}[/green]")

    # Artwork subdirectory
    artwork_subdir = path / config.artwork_subdir
    if artwork_subdir.exists() and artwork_subdir.is_dir():
        artwork_subdir_target = target_dir / config.artwork_subdir
        if artwork_subdir != artwork_subdir_target:
            dir_moves.append((artwork_subdir, artwork_subdir_target))
            rel = display_relative(artwork_subdir_target, lib_root)
            console.print(
                f"[cyan]{artwork_subdir.name}/[/cyan] -> [green]{rel}/[/green]"
            )

    return dir_moves


def get_rate_limit_str(client: DiscogsClient) -> str:
    """Return a rate-limit suffix string and log it, or ``""``."""
    rl = client.rate_limit_info
    if rl.remaining is not None and rl.limit is not None:
        logger.info(
            "Rate limit: {}/{} remaining",
            rl.remaining,
            rl.limit,
        )
        return f" | Rate limit: {rl.remaining}/{rl.limit} remaining"
    return ""


def count_artwork_saved(
    artwork_data: bytes | None,
    all_images_data: list[bytes],
    config: AppConfig,
) -> int:
    """Return how many artwork files were (or would be) saved."""
    if not artwork_data:
        return 0
    if config.image_handling not in (
        ImageHandling.SAVE,
        ImageHandling.BOTH,
    ):
        return 0
    count = 1  # primary artwork
    if config.collect_all_artwork:
        count += 1 + len(all_images_data)  # primary_01 + secondaries
    return count


def download_artwork(
    client: DiscogsClient,
    release: DiscogsRelease,
    config: AppConfig,
    *,
    silent: bool = False,
) -> tuple[bytes | None, list[bytes]]:
    """Download primary image and optional secondaries.

    When *silent* is ``True``, download failures are swallowed.
    Otherwise warnings are printed to the console.
    """
    artwork_data: bytes | None = None
    all_images_data: list[bytes] = []
    if not release.images:
        return artwork_data, all_images_data

    primary = next(
        (i for i in release.images if i.type == "primary"),
        release.images[0],
    )
    try:
        artwork_data = client.download_image(primary.resource_url)

        if config.collect_all_artwork and len(release.images) > 1:
            for img in release.images:
                if img.resource_url == primary.resource_url:
                    continue
                try:
                    img_data = client.download_image(img.resource_url)
                    all_images_data.append(img_data)
                except DiscogsAPIError as exc:
                    if not silent:
                        console.print(
                            "[yellow]Warning: Failed"
                            " to download additional"
                            f" artwork: {exc}[/yellow]"
                        )
    except DiscogsAPIError as exc:
        if not silent:
            console.print(
                f"[yellow]Warning: Failed to download artwork: {exc}[/yellow]"
            )
    return artwork_data, all_images_data


def save_release_files(
    dest: Path,
    release: DiscogsRelease,
    artwork_data: bytes | None,
    all_images_data: list[bytes],
    config: AppConfig,
) -> None:
    """Write the release info file and save artwork into *dest*."""
    write_release_info(dest, release, filename=config.info_filename)
    if artwork_data and config.image_handling in (
        ImageHandling.SAVE,
        ImageHandling.BOTH,
    ):
        save_artwork(dest, artwork_data, filename=config.artwork_filename)
        if config.collect_all_artwork:
            save_artwork(
                dest,
                artwork_data,
                filename="primary_01.jpg",
                is_primary=False,
                subdir=config.artwork_subdir,
            )
            for idx, img_data in enumerate(all_images_data, start=1):
                save_artwork(
                    dest,
                    img_data,
                    filename=f"secondary_{idx:02d}.jpg",
                    is_primary=False,
                    subdir=config.artwork_subdir,
                )
