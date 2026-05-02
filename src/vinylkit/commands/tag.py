"""scan, tag, and rename commands."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click
from click.exceptions import Exit as ClickExit
from loguru import logger
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from vinylkit.commands import _helpers
from vinylkit.exceptions import FileOperationError, TaggingError, VinylkitError
from vinylkit.models import AppConfig, TagMode

if TYPE_CHECKING:
    from vinylkit.models import DiscogsRelease


_SCAN_EPILOG = (
    "[bold]Examples:[/bold]"
    "\n\n  vinylkit scan"
    "\n\n  vinylkit scan ./recordings ./other-folder"
)


@click.command(epilog=_SCAN_EPILOG)
@click.argument(
    "paths",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    nargs=-1,
)
@click.pass_obj
def scan(config: AppConfig, paths: tuple[Path, ...]) -> None:
    """Scan folders and report on audio files and their tag status.

    Detects MP3 and FLAC files and classifies each as UNTAGGED,
    PARTIAL, or TAGGED.  If no paths are provided, the
    recordings_root (if set) or library_root is scanned.
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
        _helpers.console.print(
            f"\n[bold]Total files found:[/bold] [cyan]{len(files)}[/cyan]"
        )


_TAG_EPILOG = (
    "[bold]Examples:[/bold]"
    "\n\n  vinylkit tag --id 19983 ./recordings"
    "\n\n  vinylkit tag --artist 'Faithless' --album 'Insomnia'"
    "\n\n  vinylkit tag --id 53088 --rename --auto-move"
    "\n\n  vinylkit tag --id 53088 --rename --auto-move --delete-source"
    "\n\n  vinylkit tag --id 391682,30038,12345"
    " --library-root /path/to/library --rename --auto-move --delete-source"
    "\n\n  vinylkit tag /path/to/unsorted --id 182338,74044"
    " --library-root /path/to/library --rename --auto-move"
    "\n\n  vinylkit tag --id 28203 --merge --no-artwork"
    "\n\n  vinylkit tag --dry-run --id 6108 ./vinyl-rips"
    "\n\n  vinylkit tag --batch --auto-move"
    "\n\n  vinylkit tag --batch --no-move"
)


@click.command(epilog=_TAG_EPILOG)
@click.argument(
    "paths",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    nargs=-1,
)
@click.option(
    "--id",
    "release_id_raw",
    type=str,
    help="Discogs Release ID, or comma-separated list of IDs.",
)
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
@click.option(
    "--batch",
    is_flag=True,
    help=(
        "Batch mode: iterate subfolders, extract Discogs"
        " IDs from folder names, and tag each automatically."
    ),
)
@click.option(
    "--no-move",
    is_flag=True,
    help="Rename files in place but skip moving them to the library.",
)
@click.option(
    "--delete-source",
    is_flag=True,
    help="Delete the source folder after files are successfully moved to the library.",
)
@click.pass_obj
def tag(
    config: AppConfig,
    paths: tuple[Path, ...],
    release_id_raw: str | None,
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
    batch: bool,
    no_move: bool,
    delete_source: bool,
) -> None:
    """Tag audio files in folders using metadata from Discogs.

    Search for a release, select the correct match, and write
    ID3v2 (MP3) or Vorbis (FLAC) tags.  Use --rename to
    automatically move files into your library afterwards.
    """
    lib_root = lib_root_override or config.library_root
    tag_mode = TagMode.MERGE if merge else config.tag_mode

    # Parse --id: single int or comma-separated list
    release_ids: list[int] = []
    if release_id_raw:
        for part in release_id_raw.split(","):
            part = part.strip()
            if not part.isdigit():
                raise click.BadParameter(
                    f"{part!r} is not a valid integer.",
                    param_hint="'--id'",
                )
            release_ids.append(int(part))

    release_id: int | None = release_ids[0] if len(release_ids) == 1 else None

    if batch and (release_ids or query or artist or album or fmt_filter):
        raise click.UsageError(
            "--batch cannot be combined with"
            " --id, --search, --artist, --album, or --format."
        )

    if no_move and auto_move:
        raise click.UsageError("--no-move and --auto-move are mutually exclusive.")

    if len(release_ids) > 1 and len(paths) > 1:
        raise click.UsageError(
            "--id with multiple IDs cannot be combined with multiple paths."
        )

    # Handle multiple formats
    if fmt_filter:
        search_formats: list[str] = [f.strip() for f in fmt_filter.split(",")]
    else:
        search_formats = config.default_format

    # Resolve paths when none provided
    if not paths:
        if release_ids:
            if len(release_ids) == 1:
                # Single ID: try {root}/{id}/ first, fall back to recordings_root.
                candidate = _find_id_folder(
                    release_ids[0], config.recordings_root, lib_root
                )
                if candidate is not None:
                    paths = (candidate,)
                elif config.recordings_root:
                    paths = (config.recordings_root,)
                else:
                    raise click.UsageError(
                        f"No folder named '{release_ids[0]}' found in"
                        f" library-root ({lib_root})"
                        " and 'recordings_root' is not configured."
                    )
            else:
                # Multiple IDs: each must have its own named folder — no ambiguity.
                resolved: list[Path] = []
                for rid in release_ids:
                    candidate = _find_id_folder(rid, config.recordings_root, lib_root)
                    if candidate is None:
                        raise click.UsageError(
                            f"No folder named '{rid}' found in"
                            f" library-root ({lib_root})"
                            + (
                                f" or recordings_root ({config.recordings_root})"
                                if config.recordings_root
                                else ""
                            )
                            + "."
                        )
                    resolved.append(candidate)
                paths = tuple(resolved)
            if do_rename is None:
                do_rename = True
        elif config.recordings_root:
            paths = (config.recordings_root,)
            if do_rename is None:
                do_rename = True
        else:
            raise click.UsageError(
                "No PATH provided and 'recordings_root' is not configured."
            )

    if no_move and do_rename is None:
        do_rename = True
    if do_rename is None:
        do_rename = False

    if batch:
        _batch_tag(
            paths,
            config,
            tag_mode,
            lib_root,
            dry_run=dry_run,
            no_artwork=no_artwork,
            do_rename=do_rename,
            auto_move=auto_move,
            no_move=no_move,
            delete_source=delete_source,
        )
        return

    # Build (path, release_id) pairs for the main loop
    path_id_pairs: list[tuple[Path, int | None]]
    if len(release_ids) > 1 and len(paths) == 1:
        # Single search root + multiple IDs: resolve each ID as a subfolder.
        search_root = paths[0]
        resolved_pairs: list[tuple[Path, int | None]] = []
        for rid in release_ids:
            candidate = search_root / str(rid)
            if candidate.is_dir():
                resolved_pairs.append((candidate, rid))
            else:
                raise click.UsageError(
                    f"No folder named '{rid}' found in {search_root}."
                )
        path_id_pairs = resolved_pairs
    elif len(release_ids) > 1:
        path_id_pairs = list(zip(paths, release_ids, strict=True))
    else:
        path_id_pairs = [(p, release_id) for p in paths]

    if (
        not release_ids
        and not query
        and not artist
        and not album
        and not auto_move
        and len(paths) > 1
    ):
        _helpers.console.print(
            "[yellow]Batch mode: You will be prompted for each folder.[/yellow]"
        )

    client = _helpers.get_client(config)

    for path, current_release_id in path_id_pairs:
        _helpers.console.print(f"\n[bold blue]Processing folder:[/bold blue] {path}")
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

            effective_path = _resolve_release_folder(path, current_release_id)
            _tag_folder(
                client,
                effective_path,
                current_release_id,
                config,
                tag_mode,
                lib_root,
                dry_run=dry_run,
                no_artwork=no_artwork,
                do_rename=do_rename,
                auto_move=auto_move,
                no_move=no_move,
                delete_source=delete_source,
            )

        except (VinylkitError, OSError) as e:
            _helpers.console.print(
                f"[bold red]Tagging failed for {path.name}:[/bold red] {e}"
            )


def _find_id_folder(
    release_id: int,
    recordings_root: Path | None,
    lib_root: Path,
) -> Path | None:
    """Return the first directory named exactly *release_id* found in
    recordings_root (if set) or lib_root.  Single stat call per root — no scan.
    """
    for root in (recordings_root, lib_root):
        if root is not None:
            candidate = root / str(release_id)
            if candidate.is_dir():
                return candidate
    return None


def _resolve_release_folder(path: Path, release_id: int) -> Path:
    """Return the subfolder matching release_id if path has no audio files directly."""
    if _helpers.collect_audio_files(path):
        return path
    matches = sorted(
        f
        for f in path.iterdir()
        if f.is_dir() and _helpers.extract_id(f.name) == release_id
    )
    if not matches:
        return path
    if len(matches) > 1:
        names = ", ".join(f.name for f in matches)
        _helpers.console.print(
            f"[yellow]Warning: multiple subfolders match ID"
            f" {release_id} ({names}); using {matches[0].name}.[/yellow]"
        )
    _helpers.console.print(f"[dim]→ Found release folder: {matches[0].name}[/dim]")
    return matches[0]


def _batch_tag(
    paths: tuple[Path, ...],
    config: AppConfig,
    tag_mode: TagMode,
    lib_root: Path,
    *,
    dry_run: bool,
    no_artwork: bool,
    do_rename: bool,
    auto_move: bool,
    no_move: bool,
    delete_source: bool,
) -> None:
    """Iterate subfolders, extract Discogs IDs, and tag each."""
    client: _helpers.DiscogsClient | None = None
    succeeded = 0
    failed = 0
    skipped = 0

    for parent in paths:
        subfolders = sorted(f for f in parent.iterdir() if f.is_dir())
        for folder in subfolders:
            rid = _helpers.extract_id(folder.name)
            if rid is None:
                _helpers.console.print(
                    f"[yellow]Skipping {folder.name}:"
                    " no Discogs ID found in"
                    " folder name.[/yellow]"
                )
                skipped += 1
                continue

            _helpers.console.print(
                f"\n[bold blue]Batch:[/bold blue] {folder.name} (ID {rid})"
            )

            try:
                if client is None:
                    client = _helpers.get_client(config)
                release = client.get_release(rid)
                audio_files = _helpers.collect_audio_files(folder)
                num_files = len(audio_files)
                num_tracks = len(release.tracklist)

                if num_files != num_tracks:
                    artist_str = ", ".join(release.artists)
                    _helpers.console.print(
                        f"[bold red]Skipping {folder.name}:[/bold red]"
                        f"\n  Found {num_files} audio file(s) but Discogs"
                        f' release "{artist_str} - {release.title}"'
                        f" has {num_tracks} track(s)."
                        " Fix the folder contents and retry."
                    )
                    skipped += 1
                    continue

                _tag_folder(
                    client,
                    folder,
                    rid,
                    config,
                    tag_mode,
                    lib_root,
                    dry_run=dry_run,
                    no_artwork=no_artwork,
                    do_rename=do_rename,
                    auto_move=auto_move,
                    no_move=no_move,
                    delete_source=delete_source,
                    rename_folder=True,
                    release=release,
                )
                succeeded += 1
            except (VinylkitError, OSError) as e:
                _helpers.console.print(
                    f"[bold red]Failed {folder.name}:[/bold red] {e}"
                )
                failed += 1

    total = succeeded + failed + skipped
    summary = Text()
    summary.append(f"{succeeded} succeeded", style="bold green")
    summary.append("  ")
    summary.append(
        f"{failed} failed",
        style="bold red" if failed else "dim",
    )
    summary.append("  ")
    summary.append(
        f"{skipped} skipped",
        style="bold yellow" if skipped else "dim",
    )
    summary.append(f"  ({total} total)")
    _helpers.console.print()
    _helpers.console.print(
        Panel(summary, title="[bold]Batch Summary[/bold]", expand=False)
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
                raise ClickExit(0)
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
    no_move: bool = False,
    delete_source: bool = False,
    rename_folder: bool = False,
    release: DiscogsRelease | None = None,
) -> None:
    """Fetch a release, tag files in *path*, and optionally rename."""
    from loguru import logger

    if release is None:
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

    def tag_one(i: int, file_path: Path) -> Path | None:
        """Helper to tag a single file, intended for parallel execution."""
        try:
            if config.backup_enabled and config.backup_dir and not dry_run:
                try:
                    _helpers.backup_file(file_path, config.backup_dir)
                except OSError as e:
                    _helpers.console.print(
                        f"[yellow]Warning: Failed to backup"
                        f" {file_path.name}: {e}[/yellow]"
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
            return file_path
        except (VinylkitError, OSError) as e:
            _helpers.console.print(
                f"[bold red]Failed to tag {file_path.name}:[/bold red] {e}"
            )
            return None

    with _helpers.console.status("[bold green]Tagging files..."):
        futures: list[concurrent.futures.Future[Path | None]] = []
        # Use a reasonable number of threads for I/O bound tasks over network.
        # Max 8 threads to avoid overwhelming the NAS while still overlapping latency.
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for i, file_path in enumerate(audio_files):
                if i >= len(release.tracklist):
                    break
                futures.append(executor.submit(tag_one, i, file_path))

            # Collect results in order to preserve track indexing for renaming.
            # We wait for all futures so that we attempt to tag as many files
            # as possible, but we must track if any failed.
            failed_count = 0
            for future in futures:
                try:
                    res = future.result()
                    if res:
                        tagged_paths.append(res)
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Unexpected error in tagging thread: {e}")
                    failed_count += 1

            if failed_count > 0:
                raise TaggingError(
                    f"{failed_count} file(s) failed to tag in this folder."
                )

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
        _helpers.console.print()
        _helpers.console.print(
            Panel(
                f"[bold yellow]No files were modified.[/bold yellow]"
                f"\n[dim]{path.name}[/dim]",
                title="[bold yellow]Dry-run complete[/bold yellow]",
                expand=False,
                border_style="yellow",
            )
        )
    else:
        summary_parts = [
            f"[green]Tagged {len(tagged_paths)} tracks[/green]",
            f"[cyan]Saved {artwork_count} artwork file(s)[/cyan]",
        ]
        if rate_str:
            summary_parts.append(f"[dim]{rate_str.lstrip(' |')}[/dim]")
        _helpers.console.print()
        _helpers.console.print(
            Panel(
                "\n".join(summary_parts),
                title="[bold green]Tagging Complete[/bold green]",
                expand=False,
                border_style="green",
            )
        )

        if do_rename:
            try:
                _rename_after_tag(
                    path,
                    tagged_paths,
                    release,
                    config,
                    lib_root,
                    auto_move=auto_move,
                    no_move=no_move,
                    delete_source=delete_source,
                    rename_folder=rename_folder,
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
    no_move: bool = False,
    delete_source: bool = False,
    rename_folder: bool = False,
) -> None:
    """Rename/move files after tagging.

    Uses a two-phase approach:

    1. **Rename in-place** — audio files are renamed to their final
       filenames inside the source folder so that they always have
       correct names, even if the subsequent move fails.
    2. **Move to library** — renamed files (and supplementary files
       like artwork / release info) are moved to *lib_root*.
       Skipped when *no_move* is ``True``.

    When *no_move* is ``True`` and *rename_folder* is ``True``
    (batch mode), the source folder is renamed.  Otherwise a new
    subfolder is created inside *path* and files are moved there.
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
        track = release.tracklist[i]
        _helpers.console.print(
            f"[cyan]{track.position} - {track.title}[/cyan] -> [green]{rel}[/green]"
        )

    # Pre-flight: detect collisions among targets.
    # We check this early to avoid partial renames on disk.
    target_seen: set[Path] = set()
    for _src, dst in audio_moves:
        if dst in target_seen:
            raise FileOperationError(
                "Two or more tracks would collide at the destination. "
                "Check for duplicate track titles in the release."
            )
        target_seen.add(dst)

    # Phase 1: Rename audio files in-place so they have correct
    # names even if the cross-drive move in Phase 2 fails.
    # Note: We keep this two-phase approach for safety, but other
    # optimizations (parallel tagging, atomic saves) provide the
    # primary performance gains.
    renamed: list[tuple[Path, Path]] = []
    for src, dst in audio_moves:
        local_dst = src.parent / dst.name
        if src != local_dst:
            _helpers.move_file(src, local_dst, dry_run=False)
        renamed.append((local_dst, dst))

    if no_move:
        if not audio_moves:
            return
        # Full relative dir from naming pattern (e.g. Artist/2000 - Album)
        relative_dir = audio_moves[0][1].relative_to(lib_root).parent
        if rename_folder:
            # Batch mode: build structure alongside the source folder.
            new_folder = path.parent / relative_dir
            new_folder.mkdir(parents=True, exist_ok=True)
            for local_src, _dst in renamed:
                target = new_folder / local_src.name
                if local_src != target:
                    _helpers.move_file(local_src, target, dry_run=False)
            # Move supplementary files into new structure.
            for name in (
                config.info_filename,
                config.artwork_filename,
            ):
                src_file = path / name
                if src_file.exists():
                    _helpers.move_file(src_file, new_folder / name, dry_run=False)
            art_subdir = path / config.artwork_subdir
            if art_subdir.exists() and art_subdir.is_dir():
                _helpers.move_directory(
                    art_subdir,
                    new_folder / config.artwork_subdir,
                    dry_run=False,
                )
            # Remove empty original folder.
            if path != new_folder:
                if not any(path.iterdir()):
                    try:
                        path.rmdir()
                    except OSError as exc:
                        logger.debug(
                            "Could not remove original folder {}: {}", path, exc
                        )
                else:
                    remaining = sorted(f.name for f in path.iterdir())
                    logger.debug(
                        "Original folder {} not removed because it is not empty. "
                        "Remaining files: {}",
                        path,
                        ", ".join(remaining),
                    )
            display = str(relative_dir).replace("\\", "/")
            _helpers.console.print(
                f"\n[bold green]Files renamed into {display}.[/bold green]"
            )
        else:
            # Single release: files are already renamed in-place above.
            _helpers.console.print(
                f"\n[bold green]Files renamed in {path.name}.[/bold green]"
            )
        _helpers.collect_audio_files.cache_clear()
        return

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
        # Clear the directory listing cache as the source folder is now empty (or gone)
        _helpers.collect_audio_files.cache_clear()
        if delete_source and path.exists():
            if not any(path.iterdir()):
                try:
                    path.rmdir()
                    # Only print if it's actually gone (handles Windows delays/locks)
                    if not path.exists():
                        _helpers.console.print(
                            f"[dim]Removed empty source folder: {path.name}[/dim]"
                        )
                except OSError as exc:
                    _helpers.console.print(
                        f"[yellow]Warning: Could not remove source"
                        f" folder {path.name}: {exc}[/yellow]"
                    )
            else:
                remaining = sorted(f.name for f in path.iterdir())
                logger.debug(
                    "Folder {} not removed because it is not empty. "
                    "Remaining files: {}",
                    path,
                    ", ".join(remaining),
                )
    except VinylkitError as exc:
        _helpers.console.print(
            f"\n[bold red]Move to library"
            f" failed:[/bold red] {exc}"
            f"\n[yellow]Files were tagged and"
            f" renamed in {path}.[/yellow]"
        )


_RENAME_EPILOG = (
    "[bold]Examples:[/bold]"
    "\n\n  vinylkit rename ./recordings --id 6108"
    "\n\n  vinylkit rename ./recordings --id 6108 --commit"
    "\n\n  vinylkit rename --id 6108 --library-root /alt/path --commit"
)


@click.command(epilog=_RENAME_EPILOG)
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
    """Rename and organize audio files using metadata from Discogs.

    Generates file paths from the naming_pattern template and
    Discogs metadata.  Defaults to dry-run — use --commit to
    actually move files.
    """
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
                track = release.tracklist[i]
                _helpers.console.print(
                    f"[cyan]{track.position} - {track.title}[/cyan]"
                    f" -> [green]{rel}[/green]"
                )

            target_dir = moves[0][1].parent if moves else path
            dir_moves = _helpers.plan_supplementary_moves(
                path, target_dir, lib_root, config, moves
            )

            if dry_run:
                _helpers.console.print()
                _helpers.console.print(
                    Panel(
                        "[bold yellow]Dry-run: No files were"
                        " moved.[/bold yellow]"
                        f"\n[dim]{path.name}[/dim]"
                        "\n\nUse [bold]--commit[/bold] to apply"
                        " these changes.",
                        title="[bold yellow]Dry-run[/bold yellow]",
                        expand=False,
                        border_style="yellow",
                    )
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
