from __future__ import annotations

import logging
import shutil
from pathlib import Path

from vinylkit.exceptions import FileOperationError
from vinylkit.models import DiscogsRelease
from vinylkit.utils import sanitize_filename

logger = logging.getLogger(__name__)


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

    placeholders = {
        "artist": sanitize_filename(", ".join(release.artists)),
        "album": sanitize_filename(release.title),
        "year": str(release.year or ""),
        "track_number": sanitize_filename(track.position),
        "title": sanitize_filename(track.title),
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

    # Ensure extension is added correctly
    p = Path(relative_path)
    if p.suffix.lower() != extension.lower():
        p = p.with_suffix(extension)

    return root / p


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
        # atomic replace
        source.replace(target)
        logger.info(f"Moved: {source.name} -> {target}")
    except Exception as e:
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

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(source), str(target))
        logger.info(f"Moved directory: {source.name} -> {target}")
    except Exception as e:
        raise FileOperationError(
            f"Failed to move directory {source} to {target}: {e}"
        ) from e
