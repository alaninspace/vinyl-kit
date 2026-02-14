from __future__ import annotations

import csv
import logging
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import click
from loguru import logger
from platformdirs import user_log_dir
from rich.console import Console
from rich.table import Table

from vinylkit.config import get_config_path, load_config, save_config
from vinylkit.discogs import DiscogsClient
from vinylkit.exceptions import DiscogsAPIError, VinylkitError
from vinylkit.models import (
    AppConfig,
    AuthMode,
    DiscMapping,
    ImageHandling,
    TagMode,
    TrackNumbering,
)
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

# Configure console
console = Console()


class _InterceptHandler(logging.Handler):
    """Route stdlib log records (httpx, authlib) through loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # Find caller from where the logged message originated
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def initialise_logging(config: AppConfig) -> None:
    """Configure loguru sinks based on user settings."""
    logger.remove()

    # Console sink at user-configured level
    logger.add(
        sys.stderr,
        level=config.log_level,
        format="<level>{level: <8}</level> | {message}",
        colorize=True,
    )

    # File sink (if enabled)
    if config.log_to_file:
        log_path = config.log_file or (
            Path(user_log_dir("vinylkit", ensure_exists=True)) / "vinylkit.log"
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_path,
            level="DEBUG",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8}"
                " | {name}:{function}:{line} | {message}"
            ),
            rotation=config.log_rotation,
            retention=config.log_retention,
            encoding="utf-8",
        )

    # Bridge stdlib logging (httpx, authlib) through loguru
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)


# Constants for Discogs API - These can now be overridden by config
DEFAULT_CONSUMER_KEY = "placeholder_key"
DEFAULT_CONSUMER_SECRET = "placeholder_secret"


def get_client(config: AppConfig) -> DiscogsClient:
    """Helper to initialize DiscogsClient with appropriate credentials."""
    key = config.consumer_key or DEFAULT_CONSUMER_KEY
    secret = config.consumer_secret or DEFAULT_CONSUMER_SECRET
    return DiscogsClient(
        key,
        secret,
        config.discogs_token,
        config.discogs_secret,
        auth_mode=config.auth_mode.value,
    )


def _collect_audio_files(path: Path) -> list[Path]:
    """Collect and sort supported audio files."""
    return sorted(
        p
        for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in (".mp3", ".flac")
    )


def _display_relative(path: Path, root: Path) -> Path:
    """Return path relative to root, or the full path if not under root."""
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _check_collisions(
    moves: list[tuple[Path, Path]], dir_moves: list[tuple[Path, Path]]
) -> bool:
    """Check if any destination files or directories already exist.

    Returns True if it's safe to proceed (no collisions or user confirmed).
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


def _plan_supplementary_moves(
    path: Path,
    target_dir: Path,
    lib_root: Path,
    config: AppConfig,
    moves: list[tuple[Path, Path]],
) -> list[tuple[Path, Path]]:
    """Plan moves for info files, artwork files, and artwork subdirectories.

    Returns a list of directory moves (artwork subdirs).
    """
    dir_moves: list[tuple[Path, Path]] = []

    # Info file
    info_file = path / config.info_filename
    if info_file.exists():
        info_target = target_dir / config.info_filename
        if info_file != info_target:
            moves.append((info_file, info_target))
            rel = _display_relative(info_target, lib_root)
            console.print(f"[cyan]{info_file.name}[/cyan] -> [green]{rel}[/green]")

    # Artwork file
    artwork_file = path / config.artwork_filename
    if artwork_file.exists():
        artwork_target = target_dir / config.artwork_filename
        if artwork_file != artwork_target:
            moves.append((artwork_file, artwork_target))
            rel = _display_relative(artwork_target, lib_root)
            console.print(f"[cyan]{artwork_file.name}[/cyan] -> [green]{rel}[/green]")

    # Artwork subdirectory
    artwork_subdir = path / config.artwork_subdir
    if artwork_subdir.exists() and artwork_subdir.is_dir():
        artwork_subdir_target = target_dir / config.artwork_subdir
        if artwork_subdir != artwork_subdir_target:
            dir_moves.append((artwork_subdir, artwork_subdir_target))
            rel = _display_relative(artwork_subdir_target, lib_root)
            console.print(
                f"[cyan]{artwork_subdir.name}/[/cyan] -> [green]{rel}/[/green]"
            )

    return dir_moves


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """VinylKit: Manage your digitized vinyl collection with Discogs metadata."""
    ctx.obj = load_config()
    initialise_logging(ctx.obj)


@cli.command()
@click.argument(
    "paths",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    nargs=-1,
)
@click.pass_obj
def scan(config: AppConfig, paths: tuple[Path, ...]) -> None:
    """Scan folders and report on audio files and their tag status.

    If no paths are provided, the recordings_root (if set) or library_root is scanned.
    """
    if paths:
        scan_paths = list(paths)
    elif config.recordings_root:
        scan_paths = [config.recordings_root]
    else:
        scan_paths = [config.library_root]

    for scan_path in scan_paths:
        console.print(f"\nScanning: [bold]{scan_path}[/bold]...")

        files = scan_folder(scan_path)
        if not files:
            console.print("[yellow]No supported audio files found.[/yellow]")
            continue

        table = Table(title=f"Inventory for {scan_path.name}")
        table.add_column("File", style="cyan")
        table.add_column("Format", style="magenta")
        table.add_column("Status", style="green")

        for f in files:
            display_name = _display_relative(f.path, scan_path)
            table.add_row(str(display_name), f.extension, f.tag_status.name)

        console.print(table)
        console.print(f"[bold]Total files found:[/bold] {len(files)}")


@cli.command()
@click.argument(
    "paths",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    nargs=-1,
)
@click.option("--id", "release_id", type=int, help="Discogs Release ID.")
@click.option("--search", "query", type=str, help="Search query for Discogs.")
@click.option("--artist", type=str, help="Filter search by artist name.")
@click.option("--album", type=str, help="Filter search by album/release title.")
@click.option(
    "--format", "fmt_filter", type=str, help="Filter search by format (e.g. Vinyl, CD)."
)
@click.option(
    "--auto-move", is_flag=True, help="Automatically move files without confirmation."
)
@click.option(
    "--dry-run", is_flag=True, help="Display changes without writing to files."
)
@click.option("--no-artwork", is_flag=True, help="Disable artwork embedding.")
@click.option(
    "--rename/--no-rename",
    "do_rename",
    default=None,
    help="Automatically rename and move files after tagging.",
)
@click.option(
    "--library-root",
    "lib_root_override",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Override the library root directory for renaming.",
)
@click.option(
    "--merge",
    is_flag=True,
    help="Preserve existing tags (default is to clear and replace).",
)
@click.pass_obj
def tag(
    config: AppConfig,
    paths: tuple[Path, ...],
    release_id: int | None,
    query: str | None,
    artist: str | None,
    album: str | None,
    fmt_filter: str | None,
    auto_move: bool,
    dry_run: bool,
    no_artwork: bool,
    do_rename: bool | None,
    lib_root_override: Path | None,
    merge: bool,
) -> None:
    """Tag audio files in folders using metadata from Discogs."""
    lib_root = lib_root_override or config.library_root
    tag_mode = TagMode.MERGE if merge else config.tag_mode

    # Handle multiple formats
    if fmt_filter:
        search_formats: list[str] = [f.strip() for f in fmt_filter.split(",")]
    else:
        search_formats = config.default_format

    # Use recordings_root if no paths provided
    if not paths:
        if config.recordings_root:
            paths = (config.recordings_root,)
            # If we are using the default recordings folder,
            # assume we want to rename/move to library
            if do_rename is None:
                do_rename = True
        else:
            raise click.UsageError(
                "No PATH provided and 'recordings_root' is not configured."
            )

    # Default do_rename to False if still None (explicitly provided paths but no flag)
    if do_rename is None:
        do_rename = False

    if not release_id and not query and not artist and not album and len(paths) > 1:
        console.print(
            "[yellow]Batch mode: You will be prompted for each folder.[/yellow]"
        )

    client = get_client(config)

    for path in paths:
        console.print(f"\n[bold blue]Processing folder:[/bold blue] {path}")
        current_release_id = release_id
        current_query = query
        current_artist = artist
        current_album = album

        try:
            while True:  # Search/Retry loop for this folder
                if (
                    not current_release_id
                    and not current_query
                    and not current_artist
                    and not current_album
                ):
                    current_query = click.prompt(
                        f"Enter search query or Release ID for {path.name}"
                    )
                    if current_query.isdigit():
                        current_release_id = int(current_query)
                        current_query = None

                if current_release_id:
                    break  # Have ID, proceed to fetch

                if current_query or current_artist or current_album:
                    # Paginated search logic
                    all_results = client.search_releases(
                        current_query,
                        artist=current_artist,
                        album=current_album,
                        format=search_formats,
                    )
                    if not all_results:
                        console.print(
                            "[yellow]No results found for query/filters.[/yellow]"
                        )
                        current_query = None  # Reset to prompt again
                        current_artist = None
                        current_album = None
                        continue

                    page_size = config.search_page_size
                    offset = 0
                    selected_release_id = None
                    break_search_loop = False
                    choice = ""

                    while offset < len(all_results):
                        page_results = all_results[offset : offset + page_size]
                        search_term = current_query or current_artist or current_album
                        page_num = offset // page_size + 1
                        table_title = (
                            f"\nSearch Results for:"
                            f" [bold cyan]{search_term}[/bold cyan]"
                            f" (Page {page_num})"
                        )
                        table = Table(title=table_title)
                        table.add_column("#", style="dim")
                        table.add_column("ID", style="magenta")
                        table.add_column("Title", style="cyan")
                        table.add_column("Year", style="green")
                        table.add_column("Country", style="yellow")
                        table.add_column("Format", style="blue")
                        table.add_column("Link", style="dim", no_wrap=True)

                        for i, res in enumerate(page_results, offset + 1):
                            title = res.get("title", "Unknown")
                            year = str(res.get("year", "N/A"))
                            country = res.get("country", "N/A")
                            fmt = ", ".join(res.get("format", []))
                            rid = str(res.get("id"))
                            url = f"https://www.discogs.com/release/{rid}"
                            table.add_row(str(i), rid, title, year, country, fmt, url)

                        console.print(table)

                        options = f"(1-{offset + len(page_results)})"
                        prompt_msg = f"\nSelect a release {options}"
                        if offset + page_size < len(all_results):
                            prompt_msg += ", 'm' for more"
                        prompt_msg += ", 'r' to re-search, '0' to skip, or 'q' to quit"

                        choice = click.prompt(prompt_msg, type=str, default="1")

                        if choice.lower() == "m":
                            offset += page_size
                            continue
                        if choice.lower() == "q":
                            console.print("[yellow]Aborting tag session.[/yellow]")
                            return
                        if choice.lower() == "r":
                            current_query = None
                            current_artist = None
                            current_album = None
                            break_search_loop = True
                            break
                        if choice == "0":
                            break_search_loop = True
                            break

                        try:
                            idx = int(choice)
                            if 1 <= idx <= len(all_results):
                                selected_release_id = all_results[idx - 1]["id"]
                                break
                            console.print("[red]Invalid selection.[/red]")
                        except ValueError:
                            console.print("[red]Invalid input.[/red]")

                    if selected_release_id:
                        current_release_id = selected_release_id
                        break  # Proceed to fetch
                    if break_search_loop and not current_query:
                        # User skipped or wants to re-search
                        if choice == "0":
                            break  # Exit while True, goes to if not current_release_id
                        continue  # Re-starts while True to prompt for query
                    if offset >= len(all_results):
                        # End of results, prompt again
                        current_query = None
                        current_artist = None
                        current_album = None
                        continue

            if not current_release_id:
                continue

            assert current_release_id is not None
            release = client.get_release(current_release_id)
            artist_str = ", ".join(release.artists)
            release_display = (
                f"Loaded Release: [bold]{artist_str}"
                f" - {release.title}[/bold]"
                f" ({release.year})"
            )
            console.print(release_display)

            # Artwork handling
            artwork_data = None
            all_images_data = []
            if not no_artwork and release.images:
                primary_image = next(
                    (i for i in release.images if i.type == "primary"),
                    release.images[0],
                )
                try:
                    with console.status("[bold green]Downloading artwork..."):
                        artwork_data = client.download_image(primary_image.resource_url)

                        if config.collect_all_artwork and len(release.images) > 1:
                            for img in release.images:
                                if img.resource_url == primary_image.resource_url:
                                    continue
                                try:
                                    img_data = client.download_image(img.resource_url)
                                    all_images_data.append(img_data)
                                except DiscogsAPIError as e:
                                    console.print(
                                        "[yellow]Warning: Failed"
                                        " to download additional"
                                        f" artwork: {e}[/yellow]"
                                    )
                except DiscogsAPIError as e:
                    console.print(
                        f"[yellow]Warning: Failed to download artwork: {e}[/yellow]"
                    )

            audio_files = _collect_audio_files(path)

            if not audio_files:
                console.print(
                    f"[yellow]No supported audio files"
                    f" (MP3/FLAC) found in {path}.[/yellow]"
                )
                continue

            if len(audio_files) != len(release.tracklist):
                num_files = len(audio_files)
                num_tracks = len(release.tracklist)
                console.print(
                    f"[yellow]Warning: Found {num_files}"
                    f" files but release has"
                    f" {num_tracks} tracks.[/yellow]"
                )
                if not click.confirm("Proceed anyway?"):
                    continue

            # Tagging execution
            tagged_paths = []
            with console.status("[bold green]Tagging files..."):
                for i, file_path in enumerate(audio_files):
                    if i >= len(release.tracklist):
                        break

                    # Backup if enabled
                    if config.backup_enabled and config.backup_dir and not dry_run:
                        try:
                            backup_file(file_path, config.backup_dir)
                        except OSError as e:
                            console.print(
                                f"[yellow]Warning: Failed to"
                                f" backup {file_path.name}:"
                                f" {e}[/yellow]"
                            )

                    tag_audio_file(
                        file_path,
                        release,
                        i,
                        dry_run=dry_run,
                        artwork_data=artwork_data,
                        tag_mode=tag_mode,
                        track_numbering=config.track_numbering,
                        disc_mapping=config.disc_mapping,
                    )
                    tagged_paths.append(file_path)

            # Create info file
            if not dry_run:
                write_release_info(path, release, filename=config.info_filename)
                if artwork_data and config.image_handling in (
                    ImageHandling.SAVE,
                    ImageHandling.BOTH,
                ):
                    save_artwork(path, artwork_data, filename=config.artwork_filename)
                    if config.collect_all_artwork:
                        save_artwork(
                            path,
                            artwork_data,
                            filename="primary_01.jpg",
                            is_primary=False,
                            subdir=config.artwork_subdir,
                        )
                        for idx, img_data in enumerate(all_images_data, start=1):
                            save_artwork(
                                path,
                                img_data,
                                filename=f"secondary_{idx:02d}.jpg",
                                is_primary=False,
                                subdir=config.artwork_subdir,
                            )

            if dry_run:
                console.print(
                    f"\n[bold yellow]Dry-run complete for"
                    f" {path.name}. No files were"
                    " modified.[/bold yellow]"
                )
            else:
                console.print(
                    f"\n[bold green]Successfully tagged"
                    f" all files in {path.name}!"
                    "[/bold green]"
                )

                # Optional Renaming
                if do_rename:
                    console.print(
                        f"\n[bold blue]Renaming files in {path.name}...[/bold blue]"
                    )
                    moves: list[tuple[Path, Path]] = []
                    for i, source in enumerate(tagged_paths):
                        target = generate_path(
                            lib_root, config.naming_pattern, release, i, source.suffix
                        )
                        moves.append((source, target))
                        rel = _display_relative(target, lib_root)
                        console.print(
                            f"[cyan]{source.name}[/cyan] -> [green]{rel}[/green]"
                        )

                    target_dir = moves[0][1].parent if moves else path
                    dir_moves = _plan_supplementary_moves(
                        path, target_dir, lib_root, config, moves
                    )

                    if (
                        auto_move
                        or config.auto_move
                        or click.confirm("\nProceed with moving files?")
                    ):
                        if _check_collisions(moves, dir_moves):
                            for src, dst in moves:
                                move_file(src, dst, dry_run=False)
                            for src, dst in dir_moves:
                                move_directory(src, dst, dry_run=False)
                            console.print(
                                "\n[bold green]Files moved successfully.[/bold green]"
                            )
                        else:
                            console.print("\n[yellow]Move aborted by user.[/yellow]")

        except VinylkitError as e:
            console.print(f"[bold red]Tagging failed for {path.name}:[/bold red] {e}")


@cli.command()
@click.argument(
    "paths",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    nargs=-1,
)
@click.option("--id", "release_id", type=int, help="Discogs Release ID to match files.")
@click.option(
    "--commit", is_flag=True, help="Actually move the files (default is dry-run)."
)
@click.option(
    "--library-root",
    "lib_root_override",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Override the library root directory for renaming.",
)
@click.pass_obj
def rename(
    config: AppConfig,
    paths: tuple[Path, ...],
    release_id: int | None,
    commit: bool,
    lib_root_override: Path | None,
) -> None:
    """Rename and organize audio files using metadata from Discogs."""
    # Use recordings_root if no paths provided
    if not paths:
        if config.recordings_root:
            paths = (config.recordings_root,)
        else:
            raise click.UsageError(
                "No PATH provided and 'recordings_root' is not configured."
            )

    dry_run = not commit
    lib_root = lib_root_override or config.library_root
    client = get_client(config)

    for path in paths:
        console.print(f"\n[bold blue]Processing folder:[/bold blue] {path}")
        current_release_id = release_id

        try:
            if not current_release_id:
                current_release_id = click.prompt(
                    f"Enter Discogs Release ID for {path.name}", type=int
                )

            release = client.get_release(current_release_id)
            audio_files = _collect_audio_files(path)

            if not audio_files:
                console.print(f"[yellow]No audio files found in {path.name}.[/yellow]")
                continue

            moves: list[tuple[Path, Path]] = []
            for i, source in enumerate(audio_files):
                if i >= len(release.tracklist):
                    break
                target = generate_path(
                    lib_root, config.naming_pattern, release, i, source.suffix
                )
                moves.append((source, target))
                rel = _display_relative(target, lib_root)
                console.print(f"[cyan]{source.name}[/cyan] -> [green]{rel}[/green]")

            target_dir = moves[0][1].parent if moves else path
            dir_moves = _plan_supplementary_moves(
                path, target_dir, lib_root, config, moves
            )

            if dry_run:
                console.print(
                    f"\n[bold yellow]Dry-run for"
                    f" {path.name}: Use --commit to"
                    " apply these changes."
                    "[/bold yellow]"
                )
                continue

            if click.confirm(f"\nProceed with moving files in {path.name}?"):
                if _check_collisions(moves, dir_moves):
                    for src, dst in moves:
                        move_file(src, dst, dry_run=False)
                    for src, dst in dir_moves:
                        move_directory(src, dst, dry_run=False)
                    console.print(
                        f"\n[bold green]Files in {path.name}"
                        " moved successfully.[/bold green]"
                    )
                else:
                    console.print("\n[yellow]Move aborted by user.[/yellow]")

        except VinylkitError as e:
            console.print(f"[bold red]Rename failed for {path.name}:[/bold red] {e}")


def _extract_id(folder_name: str) -> int | None:
    """Extract Discogs ID from folder name pattern like '... [12345]'."""
    match = re.search(r"\[(\d+)\]$", folder_name)
    if match:
        return int(match.group(1))
    return None


def _maybe_log_rate_limit(
    client: DiscogsClient, log_entries: list[str], last_log_time: float
) -> float:
    """Append a rate limit snapshot to the log if 5+ seconds have elapsed."""
    now = time.time()
    if now - last_log_time < 5.0:
        return last_log_time
    info = client.rate_limit_info
    if info.used is not None and info.limit is not None:
        log_entries.append(
            f"  [Rate Limit] {info.used}/{info.limit} used, {info.remaining} remaining"
        )
    return now


@cli.command()
@click.argument(
    "source",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.argument(
    "destination",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--delete", is_flag=True, help="Delete source folders after successful migration."
)
@click.option(
    "--replace-artwork",
    is_flag=True,
    default=None,
    help="Replace existing artwork in tags (default uses config).",
)
@click.option(
    "--id",
    "filter_ids",
    type=str,
    help="Only migrate specific Discogs IDs (comma-separated).",
)
@click.option(
    "--dry-run", is_flag=True, help="Display changes without performing migration."
)
@click.pass_obj
def migrate(
    config: AppConfig,
    source: Path,
    destination: Path,
    delete: bool,
    replace_artwork: bool | None,
    filter_ids: str | None,
    dry_run: bool,
) -> None:
    """Migrate an existing library to the new structure."""
    do_delete = delete or config.delete_after_migration
    do_replace_art = (
        replace_artwork
        if replace_artwork is not None
        else config.replace_artwork_on_migration
    )

    # Parse filter IDs if provided
    target_ids: list[int] = []
    if filter_ids:
        try:
            target_ids = [int(i.strip()) for i in filter_ids.split(",")]
        except ValueError:
            raise click.UsageError(
                "Invalid format for --id. Use comma-separated numbers."
            )

    client = get_client(config)
    rate_log_time = time.time()
    log_file = destination / "00-Migration-Results.txt"
    log_entries: list[str] = [
        f"Migration Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Source: {source}",
        f"Destination: {destination}",
        f"Delete After: {do_delete}",
        f"Replace Artwork: {do_replace_art}",
        "================================================================================",
        "",
    ]

    # Process folders in alphabetical order
    folders = sorted([f for f in source.iterdir() if f.is_dir()])

    if not folders:
        console.print("[yellow]No folders found to migrate.[/yellow]")
        return

    for folder in folders:
        console.print(f"\n[bold blue]Migrating:[/bold blue] {folder.name}")
        rid = _extract_id(folder.name)

        # Apply filtering if enabled
        if target_ids and rid is not None and rid not in target_ids:
            console.print(
                f"[yellow]Skipping {folder.name} (ID {rid} not in filter list)[/yellow]"
            )
            continue

        while rid is None:
            choice = click.prompt(
                f"No ID found for '{folder.name}'. Enter Discogs ID, 's' to skip, or 'q' to quit",
                type=str,
            )
            if choice.lower() == "q":
                console.print("[yellow]Migration cancelled.[/yellow]")
                return
            if choice.lower() == "s":
                log_entries.append(f"SKIPPED: {folder.name} (User skipped)")
                break
            if choice.isdigit():
                rid = int(choice)
            else:
                console.print("[red]Invalid input.[/red]")

        if rid is None:
            continue

        try:
            release = client.get_release(rid)
            rate_log_time = _maybe_log_rate_limit(client, log_entries, rate_log_time)
            audio_files = _collect_audio_files(folder)

            if not audio_files:
                console.print(f"[yellow]No audio files found in {folder.name}[/yellow]")
                log_entries.append(f"SKIPPED: {folder.name} (No audio files)")
                continue

            # Mapping logic
            mapping: list[tuple[Path, int]] = []  # (Source Path, Track Index)

            # Create a lookup for release track positions and numbers
            pos_map: dict[str, int] = {}
            num_map: dict[str, int] = {}
            for i, t in enumerate(release.tracklist):
                pos_map[t.position.lower()] = i
                # Also calculate what the numeric track number WOULD be
                tn, _ = calculate_track_and_disc(
                    release, i, config.track_numbering, config.disc_mapping
                )
                num_map[tn] = i
                # Add normalized (no leading zero) versions if numeric
                if tn.isdigit():
                    num_map[str(int(tn))] = i

            tagged_map: dict[int, Path] = {}
            unmatched_tags: list[tuple[str, str]] = []  # (Filename, Tag)

            for f in audio_files:
                tn = get_track_number(f)
                if tn:
                    # Try exact match, normalized numeric match, and position match
                    tn_norm = str(int(tn)) if tn.isdigit() else tn
                    tn_lower = tn.lower()

                    if tn_lower in pos_map:
                        tagged_map[pos_map[tn_lower]] = f
                    elif tn in num_map:
                        tagged_map[num_map[tn]] = f
                    elif tn_norm in num_map:
                        tagged_map[num_map[tn_norm]] = f
                    else:
                        unmatched_tags.append((f.name, tn))
                else:
                    unmatched_tags.append((f.name, "None"))

            if len(tagged_map) == len(audio_files):
                for idx in sorted(tagged_map.keys()):
                    mapping.append((tagged_map[idx], idx))
            else:
                # Provide detailed feedback on why auto-mapping failed
                console.print(
                    f"\n[yellow]Automatic mapping failed for {folder.name}:[/yellow]"
                )
                console.print(f"  Source files: {len(audio_files)}")
                console.print(f"  Discogs tracks: {len(release.tracklist)}")
                if unmatched_tags:
                    console.print("  Unmatched or missing tags in source:")
                    for fname, tag in unmatched_tags[:5]:
                        console.print(f"    - {fname} (Tag: '{tag}')")

                # Use alphabetical if counts match
                if len(audio_files) == len(release.tracklist):
                    prompt = (
                        f"\nFile counts match ({len(audio_files)}). "
                        "Map files alphabetically to Discogs tracklist?"
                    )
                    if dry_run or click.confirm(prompt):
                        for i, f in enumerate(audio_files):
                            mapping.append((f, i))
                    else:
                        msg = (
                            "User refused alphabetical mapping after auto-match failed"
                        )
                        log_entries.append(f"SKIPPED: {folder.name} ({msg})")
                        continue
                else:
                    msg = (
                        f"File count ({len(audio_files)}) mismatch with "
                        f"Discogs tracks ({len(release.tracklist)})"
                    )
                    console.print(f"[yellow]{msg}[/yellow]")
                    log_entries.append(f"SKIPPED: {folder.name} ({msg})")
                    continue

            # Execution
            log_entries.append(f"PROCESSING: {folder.name} (ID: {rid})")
            log_entries.append(
                f"  Release: {', '.join(release.artists)} - {release.title}"
            )

            # Planned moves for logging
            planned_moves: list[tuple[Path, Path, int]] = []
            for src, idx in mapping:
                track_num, _ = calculate_track_and_disc(
                    release, idx, config.track_numbering, config.disc_mapping
                )
                dst = generate_path(
                    destination, config.naming_pattern, release, idx, src.suffix
                )
                planned_moves.append((src, dst, idx))
                # Use str(Path) to get platform-specific separators in log
                rel_dst = dst.relative_to(destination)
                log_entries.append(f"    {src.name} -> {rel_dst}")

            if dry_run:
                console.print(
                    "[yellow]Dry-run: Migration steps logged to memory.[/yellow]"
                )
                log_entries.append("  (Dry-run: No files were moved or modified)")
                log_entries.append("")
                continue

            # Real implementation
            with console.status(f"[green]Migrating {folder.name}..."):
                # 1. Download artwork if needed
                artwork_data = None
                all_images_data: list[bytes] = []
                if do_replace_art or config.image_handling != ImageHandling.NONE:
                    if release.images:
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
                                        img_data = client.download_image(
                                            img.resource_url
                                        )
                                        all_images_data.append(img_data)
                                    except DiscogsAPIError:
                                        pass
                        except DiscogsAPIError:
                            pass

                rate_log_time = _maybe_log_rate_limit(
                    client, log_entries, rate_log_time
                )

                # 2. Copy and tag
                for src, dst, idx in planned_moves:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

                    # Clear and re-tag
                    clear_audio_tags(dst, preserve_artwork=not do_replace_art)
                    tag_audio_file(
                        dst,
                        release,
                        idx,
                        artwork_data=artwork_data if do_replace_art else None,
                        tag_mode=TagMode.REPLACE,
                        track_numbering=config.track_numbering,
                        disc_mapping=config.disc_mapping,
                    )

                # 3. Supplementary files
                write_release_info(dst.parent, release, filename=config.info_filename)
                if artwork_data and config.image_handling in (
                    ImageHandling.SAVE,
                    ImageHandling.BOTH,
                ):
                    save_artwork(
                        dst.parent, artwork_data, filename=config.artwork_filename
                    )
                    if config.collect_all_artwork:
                        save_artwork(
                            dst.parent,
                            artwork_data,
                            filename="primary_01.jpg",
                            is_primary=False,
                            subdir=config.artwork_subdir,
                        )
                        for idx, img_data in enumerate(all_images_data, start=1):
                            save_artwork(
                                dst.parent,
                                img_data,
                                filename=f"secondary_{idx:02d}.jpg",
                                is_primary=False,
                                subdir=config.artwork_subdir,
                            )

            if do_delete:
                shutil.rmtree(folder)
                console.print(f"[green]Migrated and deleted: {folder.name}[/green]")
            else:
                console.print(f"[green]Migrated: {folder.name}[/green]")

            log_entries.append("  STATUS: Success")
            log_entries.append("")

        except Exception as e:
            console.print(f"[red]Failed to migrate {folder.name}: {e}[/red]")
            log_entries.append(f"FAILED: {folder.name} ({e})")
            log_entries.append("")

    # Append rate limit summary
    info = client.rate_limit_info
    if info.limit is not None:
        log_entries.append(
            "================================================================================"
        )
        log_entries.append("Rate Limit Summary")
        log_entries.append(f"  Peak usage: {info.peak_used}/{info.limit}")
        used_str = str(info.used) if info.used is not None else "?"
        remaining_str = str(info.remaining) if info.remaining is not None else "?"
        log_entries.append(
            f"  Final state: {used_str}/{info.limit} used, {remaining_str} remaining"
        )
        log_entries.append("")

    # Write log file
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
        log_file.write_text("\n".join(log_entries), encoding="utf-8")
        console.print(
            f"\n[bold green]Migration complete![/bold green] Results in {log_file.name}"
        )
    else:
        console.print(
            "\n[bold yellow]Dry-run complete.[/bold yellow] Migration log would have been saved."
        )


@cli.group()
def auth() -> None:
    """Manage Discogs authentication."""
    pass


@auth.command()
@click.pass_obj
def login(config: AppConfig) -> None:
    """Authenticate with Discogs using OAuth 1.0a."""
    if not config.consumer_key or config.consumer_key == DEFAULT_CONSUMER_KEY:
        console.print(
            "[bold red]Error:[/bold red] You must set your own"
            " [bold]consumer_key[/bold] and"
            " [bold]consumer_secret[/bold]"
            " before logging in."
        )
        console.print(
            "See the [bold]Authentication Guide (auth.md)[/bold] for instructions."
        )
        return

    client = get_client(config)

    try:
        url, req_token, req_token_secret = client.get_authorize_url()
        console.print(
            "\n1. Please visit this URL to authorize"
            f" VinylKit:\n[link={url}]{url}[/link]\n"
        )
        verifier = click.prompt("2. Enter the verifier code provided by Discogs")

        access_token, access_token_secret = client.complete_oauth(
            req_token, req_token_secret, verifier
        )

        # Update and save config
        new_config = AppConfig(
            library_root=config.library_root,
            consumer_key=config.consumer_key,
            consumer_secret=config.consumer_secret,
            discogs_token=access_token,
            discogs_secret=access_token_secret,
            auth_mode=config.auth_mode,
            tag_mode=config.tag_mode,
            naming_pattern=config.naming_pattern,
            image_handling=config.image_handling,
            backup_enabled=config.backup_enabled,
            backup_dir=config.backup_dir,
        )
        save_config(new_config)
        console.print(
            "[bold green]Success![/bold green] You are now authenticated with Discogs."
        )

        # Show identity
        client = get_client(new_config)
        identity_data = client.get_identity()
        console.print(f"Authenticated as: [bold]{identity_data.get('username')}[/bold]")
    except VinylkitError as e:
        console.print(f"[bold red]Authentication failed:[/bold red] {e}")


@auth.command()
@click.pass_obj
def identity(config: AppConfig) -> None:
    """Display the authenticated Discogs user."""
    client = get_client(config)
    try:
        identity_data = client.get_identity()
        console.print(f"Authenticated as: [bold]{identity_data.get('username')}[/bold]")
        name = identity_data.get("name") or "Not set"
        console.print(f"Name: {name}")
        console.print(f"URL: {identity_data.get('resource_url')}")
    except VinylkitError as e:
        console.print(f"[bold red]Failed to get identity:[/bold red] {e}")


@cli.group()
def collection() -> None:
    """Manage your Discogs collection."""
    pass


@collection.command(name="download")
@click.pass_obj
def collection_download(config: AppConfig) -> None:
    """Download your Discogs collection to a CSV file."""
    client = get_client(config)
    try:
        with console.status("[bold green]Fetching identity..."):
            identity = client.get_identity()
            username = identity.get("username")

        if not username:
            console.print("[red]Error: Could not determine username.[/red]")
            return

        with console.status(f"[bold green]Downloading collection for {username}..."):
            releases = client.get_collection_releases(username)

        if not releases:
            console.print("[yellow]No releases found in your collection.[/yellow]")
            return

        date_prefix = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_prefix}_{username}_collection.csv"
        filepath = Path.cwd() / filename

        if filepath.exists() and not click.confirm(
            f"[yellow]Warning: {filename} already exists. Overwrite?[/yellow]",
            default=False,
        ):
            console.print("[yellow]Download aborted.[/yellow]")
            return

        with filepath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(
                [
                    "release_id",
                    "Catalog#",
                    "Artist",
                    "Title",
                    "Label",
                    "Format",
                    "Released",
                ]
            )

            for r in releases:
                basic = r.get("basic_information", {})
                release_id = r.get("id")

                # Extract fields safely
                artists = ", ".join(
                    [a.get("name", "Unknown") for a in basic.get("artists", [])]
                )
                title = basic.get("title", "Unknown")
                year = basic.get("year", "N/A")

                # Labels
                labels = basic.get("labels", [])
                label_name = labels[0].get("name", "N/A") if labels else "N/A"
                catno = labels[0].get("catno", "N/A") if labels else "N/A"

                # Formats
                formats = basic.get("formats", [])
                fmt_str = formats[0].get("name", "N/A") if formats else "N/A"

                writer.writerow(
                    [release_id, catno, artists, title, label_name, fmt_str, year]
                )

        console.print(
            "[bold green]Success![/bold green]"
            f" Collection saved to [cyan]{filename}[/cyan]"
        )
        console.print(f"Total releases: {len(releases)}")

    except (VinylkitError, OSError) as e:
        console.print(f"[bold red]Failed to download collection:[/bold red] {e}")


@cli.group()
def config() -> None:
    """Manage configuration settings."""
    pass


@config.command(name="show")
@click.pass_obj
def config_show(config_obj: AppConfig) -> None:
    """Display the current configuration."""
    path = get_config_path()
    if not path.exists():
        console.print("[yellow]Config file does not exist. Showing defaults.[/yellow]")

    console.print(f"[bold]Config Path:[/bold] {path}\n")

    default_fmt = (
        ", ".join(config_obj.default_format) if config_obj.default_format else "None"
    )
    key_display = "****" if config_obj.consumer_key else "Not Set"
    token_display = "****" if config_obj.discogs_token else "Not Set"

    sections: list[tuple[str, list[tuple[str, str]]]] = [
        (
            "General",
            [
                ("library_root", str(config_obj.library_root)),
                ("recordings_root", str(config_obj.recordings_root or "Not Set")),
                ("auto_move", str(config_obj.auto_move)),
            ],
        ),
        (
            "Metadata & Tagging",
            [
                ("naming_pattern", config_obj.naming_pattern),
                ("tag_mode", config_obj.tag_mode.value),
                ("track_numbering", config_obj.track_numbering.value),
                ("disc_mapping", config_obj.disc_mapping.value),
                ("info_filename", config_obj.info_filename),
            ],
        ),
        (
            "Artwork",
            [
                ("image_handling", config_obj.image_handling.value),
                ("artwork_filename", config_obj.artwork_filename),
                ("collect_all_artwork", str(config_obj.collect_all_artwork)),
                ("artwork_subdir", config_obj.artwork_subdir),
            ],
        ),
        (
            "Safety & Backups",
            [
                ("backup_enabled", str(config_obj.backup_enabled)),
                ("backup_dir", str(config_obj.backup_dir or "Not Set")),
            ],
        ),
        (
            "Search & Discovery",
            [
                ("search_page_size", str(config_obj.search_page_size)),
                ("default_format", default_fmt),
            ],
        ),
        (
            "Library Migration",
            [
                (
                    "delete_after_migration",
                    str(config_obj.delete_after_migration),
                ),
                (
                    "replace_artwork_on_migration",
                    str(config_obj.replace_artwork_on_migration),
                ),
            ],
        ),
        (
            "Logging",
            [
                ("log_level", config_obj.log_level),
                ("log_to_file", str(config_obj.log_to_file)),
                ("log_file", str(config_obj.log_file or "Default")),
                ("log_rotation", config_obj.log_rotation),
                ("log_retention", str(config_obj.log_retention)),
            ],
        ),
        (
            "Authentication",
            [
                ("auth_mode", config_obj.auth_mode.value),
                ("discogs_token", token_display),
                ("consumer_key", key_display),
            ],
        ),
    ]

    table = Table(show_header=True, show_lines=False, pad_edge=False)
    table.add_column("Setting", style="bold cyan", no_wrap=True)
    table.add_column("Value", overflow="fold")

    for i, (section_title, rows) in enumerate(sections):
        if i > 0:
            table.add_row("", "")
        table.add_section()
        table.add_row(f"[bold magenta]{section_title}[/bold magenta]", "")
        for key, value in rows:
            table.add_row(f"  {key}", value)

    console.print(table)


def _parse_bool(value: str) -> bool:
    return value.lower() == "true"


def _parse_format_list(value: str) -> list[str]:
    if value.lower() == "none":
        return []
    return [v.strip() for v in value.split(",")]


# Maps config keys to their type converter functions
_CONFIG_CONVERTERS: dict[str, Callable[[str], Any]] = {
    "library_root": Path,
    "recordings_root": Path,
    "auth_mode": AuthMode,
    "tag_mode": TagMode,
    "track_numbering": TrackNumbering,
    "disc_mapping": DiscMapping,
    "consumer_key": str,
    "consumer_secret": str,
    "discogs_token": str,
    "naming_pattern": str,
    "image_handling": ImageHandling,
    "collect_all_artwork": _parse_bool,
    "artwork_subdir": str,
    "backup_enabled": _parse_bool,
    "backup_dir": Path,
    "info_filename": str,
    "artwork_filename": str,
    "search_page_size": int,
    "default_format": _parse_format_list,
    "auto_move": _parse_bool,
    "delete_after_migration": _parse_bool,
    "replace_artwork_on_migration": _parse_bool,
    "log_level": str,
    "log_to_file": _parse_bool,
    "log_file": Path,
    "log_rotation": str,
    "log_retention": int,
}


@config.command(name="set")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def config_set(config_obj: AppConfig, key: str, value: str) -> None:
    """Set a configuration value."""
    if key not in _CONFIG_CONVERTERS:
        console.print(f"[red]Unknown configuration key: {key}[/red]")
        return

    converter = _CONFIG_CONVERTERS[key]
    new_data = {
        field: getattr(config_obj, field) for field in AppConfig.__dataclass_fields__
    }
    new_data[key] = converter(value)

    new_config = AppConfig(**new_data)
    save_config(new_config)
    console.print(f"[green]Successfully set {key} to {value}[/green]")


def main() -> None:
    try:
        cli(obj=None)
    except VinylkitError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        logger.exception("An unexpected error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
