from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path


def backup_file(source: Path, backup_dir: Path) -> Path:
    """
    Copy a file to a backup directory, preserving metadata.

    Args:
        source: The file to back up.
        backup_dir: The directory to store backups.

    Returns:
        The path to the created backup file.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / source.name

    # Find a unique backup name to avoid overwriting existing backups
    if target.exists():
        stem = source.stem
        suffix = source.suffix
        for n in range(1, 1000):
            candidate = backup_dir / f"{stem}_backup{n}{suffix}"
            if not candidate.exists():
                target = candidate
                break
        else:
            raise OSError(f"Cannot find a free backup name for {source.name}")

    shutil.copy2(source, target)
    return target


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    Sanitize a filename by removing illegal characters and normalizing Unicode.

    Args:
        filename: The original filename string.
        replacement: The character to replace illegal characters with.

    Returns:
        A sanitized filename string.
    """
    # NFC normalization for consistent Unicode handling
    filename = unicodedata.normalize("NFC", filename)

    # Illegal characters on major platforms: <>:"/\|?*
    # Also remove control characters
    illegal_chars = r'[<>:"/\|?*\x00-\x1f]'
    sanitized = re.sub(illegal_chars, replacement, filename)

    # Truncate to 255 bytes (standard filesystem limit)
    # We use encode/decode to handle byte length correctly
    encoded = sanitized.encode("utf-8")[:255]
    return encoded.decode("utf-8", "ignore")


_DISAMBIGUATION_RE = re.compile(r"\s*\(\d+\)\s*$")


def clean_artist_name(name: str, anv: str = "") -> str:
    """Return the display name for a Discogs artist.

    Uses anv (artist name variation) when set — it reflects the name as
    credited on the release. Falls back to stripping the Discogs
    disambiguation suffix (e.g. 'Pariah (2)' → 'Pariah').
    """
    if anv.strip():
        return anv.strip()
    return _DISAMBIGUATION_RE.sub("", name).strip()


def ensure_absolute(path: Path | str, root: Path | None = None) -> Path:
    """
    Ensure a path is absolute. If relative, resolve against the provided root.

    Args:
        path: The path to resolve.
        root: The root directory to resolve against if path is relative.

    Returns:
        An absolute Path object.
    """
    p = Path(path)
    if p.is_absolute():
        return p
    if root:
        return (root / p).resolve()
    return p.resolve()
