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
    
    # Avoid overwriting if backup exists (add suffix)
    if target.exists():
        target = backup_dir / f"{source.stem}_backup{source.suffix}"
        
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
