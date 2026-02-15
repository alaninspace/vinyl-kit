"""scan, tag, and rename commands."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.table import Table

from vinylkit.commands import _helpers
from vinylkit.exceptions import VinylkitError
from vinylkit.models import AppConfig, TagMode

if TYPE_CHECKING:
    from vinylkit.models import DiscogsRelease


@click.command()
@click.argument(
    "paths",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    nargs=-1,
)
@click.pass_obj
def scan(config: AppConfig, paths: tuple[Path, ...]) -> None:
    """Scan folders and report on audio files and their tag status.

    If no paths are provided, the recordings_root (if set) or
    library_root is scanned.
    """
    if paths:
        scan_paths = list(paths)
    elif config.recordings_root:
        scan_paths = [config.recordings_root]
    else:
        scan_paths = [config.library_root]

    for scan_path in scan_paths:
        _helpers.console.print(f"\nScanning: [bold]{scan_path}[/bold]...")

        files = _helpers.scan_folder(scan_path)
        if not files:
            _helpers.console.print("[yellow]No supported audio files found.[/yellow]")
            continue

        table = Table(title=f"Inventory for {scan_path.name}")
        table.add_column("File", style="cyan")
        table.add_column("Format", style="magenta")
        table.add_column("Status", style="green")

        for f in files:
            display_name = _helpers.display_relative(f.path, scan_path)
            table.add_row(str(display_name), f.extension, f.tag_status.name)

        _helpers.console.print(table)
        _helpers.console.print(f"[bold]Total files found:[/bold] {len(files)}")


@click.command()
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
    "--format",
    "fmt_filter",
    type=str,
    help="Filter search by format (e.g. Vinyl, CD).",
)
@click.option(
    "--auto-move",
    is_flag=True,
    help="Automatically move files without confirmation.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Display changes without writing to files.",
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
            if do_rename is None:
                do_rename = True
        else:
            raise click.UsageError(
                "No PATH provided and 'recordings_root' is not configured."
            )

    if do_rename is None:
        do_rename = False

    if not release_id and not query and not artist and not album and len(paths) > 1:
        _helpers.console.print(
            "[yellow]Batch mode: You will be prompted for each folder.[/yellow]"
        )

    client = _helpers.get_client(config)

    for path in paths:
        _helpers.console.print(f"\n[bold blue]Processing folder:[/bold blue] {path}")
        current_release_id = release_id
        current_query = query
        current_artist = artist
        current_album = album

        try:
            current_release_id = _search_loop(
                client,
                path,
                current_release_id,
                current_query,
                current_artist,
                current_album,
                search_formats,
                config,
            )

            if not current_release_id:
                continue

            _tag_folder(
                client,
                path,
                current_release_id,
                config,
                tag_mode,
                lib_root,
                dry_run=dry_run,
                no_artwork=no_artwork,
                do_rename=do_rename,
                auto_move=auto_move,
            )

        except VinylkitError as e:
            _helpers.console.print(
                f"[bold red]Tagging failed for {path.name}:[/bold red] {e}"
            )


def _search_loop(
    client: _helpers.DiscogsClient,
    path: Path,
    release_id: int | None,
    query: str | None,
    artist: str | None,
    album: str | None,
    search_formats: list[str],
    config: AppConfig,
) -> int | None:
    """Run the interactive search/retry loop, returning a release ID."""
    current_release_id = release_id
    current_query = query
    current_artist = artist
    current_album = album

    while True:
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
            return current_release_id

        if current_query or current_artist or current_album:
            result = _paginated_search(
                client,
                current_query,
                current_artist,
                current_album,
                search_formats,
                config,
            )
            if result is None:
                # Re-search requested
                current_query = None
                current_artist = None
                current_album = None
                continue
            if result == 0:
                return None  # User skipped
            if result == -1:
                # Quit entire tag session
                _helpers.console.print("[yellow]Aborting tag session.[/yellow]")
                raise SystemExit(0)
            return result

        current_query = None
        current_artist = None
        current_album = None


def _paginated_search(
    client: _helpers.DiscogsClient,
    query: str | None,
    artist: str | None,
    album: str | None,
    search_formats: list[str],
    config: AppConfig,
) -> int | None:
    """Run paginated search and return selected release ID.

    Returns:
        A positive int for a selected release ID,
        ``0`` to skip, ``-1`` to quit, ``None`` to re-search.
    """
    all_results = client.search_releases(
        query,
        artist=artist,
        album=album,
        format=search_formats,
    )
    if not all_results:
        _helpers.console.print("[yellow]No results found for query/filters.[/yellow]")
        return None

    page_size = config.search_page_size
    offset = 0

    while offset < len(all_results):
        page_results = all_results[offset : offset + page_size]
        search_term = query or artist or album
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

        _helpers.console.print(table)

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
            return -1
        if choice.lower() == "r":
            return None
        if choice == "0":
            return 0

        try:
            idx = int(choice)
            if 1 <= idx <= len(all_results):
                return int(all_results[idx - 1]["id"])
            _helpers.console.print("[red]Invalid selection.[/red]")
        except ValueError:
            _helpers.console.print("[red]Invalid input.[/red]")

    # End of results
    return None


def _tag_folder(
    client: _helpers.DiscogsClient,
    path: Path,
    release_id: int,
    config: AppConfig,
    tag_mode: TagMode,
    lib_root: Path,
    *,
    dry_run: bool,
    no_artwork: bool,
    do_rename: bool,
    auto_move: bool,
) -> None:
    """Fetch a release, tag files in *path*, and optionally rename."""
    from loguru import logger

    release = client.get_release(release_id)
    artist_str = ", ".join(release.artists)
    logger.info(
        "=== Release: {} - {} (ID: {}) ===",
        artist_str,
        release.title,
        release.id,
    )
    release_display = (
        f"Loaded Release: [bold]{artist_str} - {release.title}[/bold] ({release.year})"
    )
    _helpers.console.print(release_display)

    # Artwork handling
    artwork_data: bytes | None = None
    all_images_data: list[bytes] = []
    if not no_artwork:
        with _helpers.console.status("[bold green]Downloading artwork..."):
            artwork_data, all_images_data = _helpers.download_artwork(
                client, release, config
            )

    audio_files = _helpers.collect_audio_files(path)

    if not audio_files:
        _helpers.console.print(
            f"[yellow]No supported audio files (MP3/FLAC) found in {path}.[/yellow]"
        )
        return

    if len(audio_files) != len(release.tracklist):
        num_files = len(audio_files)
        num_tracks = len(release.tracklist)
        _helpers.console.print(
            f"[yellow]Warning: Found {num_files}"
            f" files but release has"
            f" {num_tracks} tracks.[/yellow]"
        )
        if not click.confirm("Proceed anyway?"):
            return

    # Tagging execution
    tagged_paths: list[Path] = []
    with _helpers.console.status("[bold green]Tagging files..."):
        for i, file_path in enumerate(audio_files):
            if i >= len(release.tracklist):
                break

            if config.backup_enabled and config.backup_dir and not dry_run:
                try:
                    _helpers.backup_file(file_path, config.backup_dir)
                except OSError as e:
                    _helpers.console.print(
                        f"[yellow]Warning: Failed to"
                        f" backup {file_path.name}:"
                        f" {e}[/yellow]"
                    )

            _helpers.tag_audio_file(
                file_path,
                release,
                i,
                dry_run=dry_run,
                artwork_data=artwork_data,
                tag_mode=tag_mode,
                track_numbering=config.track_numbering,
                disc_mapping=config.disc_mapping,
                skip_tags=frozenset(config.skip_tags),
            )
            tagged_paths.append(file_path)

    # Save supplementary files
    if not dry_run:
        _helpers.save_release_files(
            path, release, artwork_data, all_images_data, config
        )

    artwork_count = (
        _helpers.count_artwork_saved(artwork_data, all_images_data, config)
        if not dry_run
        else 0
    )

    rate_str = _helpers.get_rate_limit_str(client)

    if dry_run:
        _helpers.console.print(
            f"\n[bold yellow]Dry-run complete for"
            f" {path.name}. No files were"
            " modified.[/bold yellow]"
        )
    else:
        summary = (
            f"Tagged {len(tagged_paths)} tracks"
            f", saved {artwork_count} artwork files"
            f"{rate_str}"
        )
        _helpers.console.print(f"\n[bold green]{summary}[/bold green]")

        if do_rename:
            try:
                _rename_after_tag(
                    path,
                    tagged_paths,
                    release,
                    config,
                    lib_root,
                    auto_move=auto_move,
                )
            except VinylkitError as e:
                _helpers.console.print(
                    f"[bold red]Rename failed for"
                    f" {path.name}:[/bold red] {e}"
                    f"\n[yellow]Note: Files were"
                    " tagged successfully.[/yellow]"
                )


def _rename_after_tag(
    path: Path,
    tagged_paths: list[Path],
    release: DiscogsRelease,
    config: AppConfig,
    lib_root: Path,
    *,
    auto_move: bool,
) -> None:
    """Rename/move files after tagging.

    Uses a two-phase approach:

    1. **Rename in-place** — audio files are renamed to their final
       filenames inside the source folder so that they always have
       correct names, even if the subsequent move fails.
    2. **Move to library** — renamed files (and supplementary files
       like artwork / release info) are moved to *lib_root*.
    """
    _helpers.console.print(f"\n[bold blue]Renaming files in {path.name}...[/bold blue]")

    # Plan audio file moves
    audio_moves: list[tuple[Path, Path]] = []
    for i, source in enumerate(tagged_paths):
        target = _helpers.generate_path(
            lib_root,
            config.naming_pattern,
            release,
            i,
            source.suffix,
        )
        audio_moves.append((source, target))
        rel = _helpers.display_relative(target, lib_root)
        _helpers.console.print(f"[cyan]{source.name}[/cyan] -> [green]{rel}[/green]")

    # moves includes audio + supplementary files (appended below)
    moves: list[tuple[Path, Path]] = list(audio_moves)
    target_dir = moves[0][1].parent if moves else path
    dir_moves = _helpers.plan_supplementary_moves(
        path, target_dir, lib_root, config, moves
    )

    if not (
        auto_move or config.auto_move or click.confirm("\nProceed with moving files?")
    ):
        _helpers.console.print("\n[yellow]Move aborted by user.[/yellow]")
        return

    if not _helpers.check_collisions(moves, dir_moves):
        _helpers.console.print("\n[yellow]Move aborted by user.[/yellow]")
        return

    # Phase 1: Rename audio files in-place so they have correct
    # names even if the cross-drive move in Phase 2 fails.
    renamed: list[tuple[Path, Path]] = []
    for src, dst in audio_moves:
        local_dst = src.parent / dst.name
        if src != local_dst:
            _helpers.move_file(src, local_dst, dry_run=False)
        renamed.append((local_dst, dst))

    # Supplementary file moves (info, artwork) appended by
    # plan_supplementary_moves — they already have correct names.
    supp_moves = moves[len(audio_moves) :]

    # Phase 2: Move renamed files + supplementary files to library.
    try:
        for local_src, dst in renamed:
            if local_src != dst:
                _helpers.move_file(local_src, dst, dry_run=False)
        for src, dst in supp_moves:
            _helpers.move_file(src, dst, dry_run=False)
        for src, dst in dir_moves:
            _helpers.move_directory(src, dst, dry_run=False)
        _helpers.console.print("\n[bold green]Files moved successfully.[/bold green]")
    except VinylkitError as exc:
        _helpers.console.print(
            f"\n[bold red]Move to library"
            f" failed:[/bold red] {exc}"
            f"\n[yellow]Files were tagged and"
            f" renamed in {path}.[/yellow]"
        )


@click.command()
@click.argument(
    "paths",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    nargs=-1,
)
@click.option(
    "--id",
    "release_id",
    type=int,
    help="Discogs Release ID to match files.",
)
@click.option(
    "--commit",
    is_flag=True,
    help="Actually move the files (default is dry-run).",
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
    if not paths:
        if config.recordings_root:
            paths = (config.recordings_root,)
        else:
            raise click.UsageError(
                "No PATH provided and 'recordings_root' is not configured."
            )

    dry_run = not commit
    lib_root = lib_root_override or config.library_root
    client = _helpers.get_client(config)

    for path in paths:
        _helpers.console.print(f"\n[bold blue]Processing folder:[/bold blue] {path}")
        current_release_id = release_id

        try:
            if not current_release_id:
                current_release_id = click.prompt(
                    f"Enter Discogs Release ID for {path.name}",
                    type=int,
                )

            release = client.get_release(current_release_id)
            audio_files = _helpers.collect_audio_files(path)

            if not audio_files:
                _helpers.console.print(
                    f"[yellow]No audio files found in {path.name}.[/yellow]"
                )
                continue

            moves: list[tuple[Path, Path]] = []
            for i, source in enumerate(audio_files):
                if i >= len(release.tracklist):
                    break
                target = _helpers.generate_path(
                    lib_root,
                    config.naming_pattern,
                    release,
                    i,
                    source.suffix,
                )
                moves.append((source, target))
                rel = _helpers.display_relative(target, lib_root)
                _helpers.console.print(
                    f"[cyan]{source.name}[/cyan] -> [green]{rel}[/green]"
                )

            target_dir = moves[0][1].parent if moves else path
            dir_moves = _helpers.plan_supplementary_moves(
                path, target_dir, lib_root, config, moves
            )

            if dry_run:
                _helpers.console.print(
                    f"\n[bold yellow]Dry-run for"
                    f" {path.name}: Use --commit to"
                    " apply these changes."
                    "[/bold yellow]"
                )
                continue

            if click.confirm(f"\nProceed with moving files in {path.name}?"):
                if _helpers.check_collisions(moves, dir_moves):
                    for src, dst in moves:
                        _helpers.move_file(src, dst, dry_run=False)
                    for src, dst in dir_moves:
                        _helpers.move_directory(src, dst, dry_run=False)
                    _helpers.console.print(
                        f"\n[bold green]Files in {path.name}"
                        " moved successfully.[/bold green]"
                    )
                else:
                    _helpers.console.print("\n[yellow]Move aborted by user.[/yellow]")

        except VinylkitError as e:
            _helpers.console.print(
                f"[bold red]Rename failed for {path.name}:[/bold red] {e}"
            )
