from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from vinylkit.exceptions import FileOperationError
from vinylkit.utils import sanitize_filename

if TYPE_CHECKING:
    from vinylkit.models import DiscogsRelease


def generate_path(
    root: Path,
    pattern: str,
    release: DiscogsRelease,
    track_index: int,
    extension: str,
) -> Path:
    """
    Generate a new file path based on a naming pattern.
    """
    track = release.tracklist[track_index]

    # Smart title: include artist prefix if track artist differs from release artist
    # (Matches write_release_info logic)
    if track.artists and track.artists != release.artists:
        full_title = f"{', '.join(track.artists)} - {track.title}"
    else:
        full_title = track.title

    placeholders = {
        "artist": sanitize_filename(", ".join(release.artists)),
        "track_artist": sanitize_filename(
            ", ".join(track.artists) if track.artists else ", ".join(release.artists)
        ),
        "album": sanitize_filename(release.title),
        "year": str(release.year or ""),
        "track_number": sanitize_filename(track.position),
        "title": sanitize_filename(track.title),
        "full_title": sanitize_filename(full_title),
        "label": sanitize_filename(release.label or ""),
        "catalogue_number": sanitize_filename(release.catno or ""),
        "side": sanitize_filename(track.side or ""),
        "id": str(release.id),
        "discogs_id": str(release.id),
        "genre": sanitize_filename(release.genres[0] if release.genres else ""),
        "style": sanitize_filename(release.styles[0] if release.styles else ""),
        "country": sanitize_filename(release.country or ""),
    }

    # Simple replacement
    try:
        relative_path = pattern.format(**placeholders)
    except KeyError as e:
        raise FileOperationError(f"Invalid placeholder in naming pattern: {e}") from e

    # Append extension directly — avoid Path.with_suffix() which uses rfind('.')
    # and misinterprets dots in filenames (e.g. vinyl positions "B.1", "B.2",
    # or titles like "Mr. Brightside") as file extensions, stripping the track
    # title from the path and causing rename collisions.
    return root / Path(relative_path + extension)


def move_file(source: Path, target: Path, dry_run: bool = False) -> None:
    """
    Safely move a file to a new location.
    """
    if source == target:
        return

    if dry_run:
        logger.info(f"[DRY-RUN] Moving {source} -> {target}")
        return

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        logger.debug(f"Moved: {source.name} -> {target}")
    except OSError as e:
        raise FileOperationError(f"Failed to move {source} to {target}: {e}") from e


def move_directory(source: Path, target: Path, dry_run: bool = False) -> None:
    """
    Safely move a directory to a new location.
    """
    if source == target:
        return

    if dry_run:
        logger.info(f"[DRY-RUN] Moving directory {source} -> {target}")
        return

    if not source.exists():
        return

    if target.exists():
        raise FileOperationError(f"Target directory already exists: {target}")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        logger.debug(f"Moved directory: {source.name} -> {target}")
    except OSError as e:
        raise FileOperationError(
            f"Failed to move directory {source} to {target}: {e}"
        ) from e
