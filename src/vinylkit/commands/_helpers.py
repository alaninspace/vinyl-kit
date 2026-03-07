"""Shared helpers, constants, and re-exported dependencies for CLI commands.

Command modules access mockable external dependencies through this module
(e.g. ``_helpers.tag_audio_file``) so that a single mock-patch target
(``vinylkit.commands._helpers.X``) covers every consumer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
from vinylkit.utils import backup_file

if TYPE_CHECKING:
    from pathlib import Path

    from vinylkit.models import DiscogsRelease

# Suppress unused-import warnings — these names are accessed by command
# modules via ``_helpers.X`` so that tests can mock them in one place.
__all__ = [
    "DiscogsClient",
    "backup_file",
    "calculate_track_and_disc",
    "clear_audio_tags",
    "describe_throttle_strategy",
    "generate_path",
    "get_cache_dir",
    "get_track_number",
    "move_directory",
    "move_file",
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
        auth_mode=config.auth_mode.value,
    )


def collect_audio_files(path: Path) -> list[Path]:
    """Collect and sort supported audio files."""
    return sorted(
        p
        for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in (".mp3", ".flac")
    )


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
