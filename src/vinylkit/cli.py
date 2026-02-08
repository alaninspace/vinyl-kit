from __future__ import annotations

import csv
import logging
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from vinylkit.config import get_config_path, load_config, save_config
from vinylkit.discogs import DiscogsClient
from vinylkit.exceptions import VinylkitError
from vinylkit.models import AppConfig, AuthMode, ImageHandling, TagMode
from vinylkit.naming import generate_path, move_directory, move_file
from vinylkit.tagging import (
    save_artwork,
    scan_folder,
    tag_audio_file,
    write_release_info,
)
from vinylkit.utils import backup_file

# Configure console and logging
console = Console()
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)

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


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """VinylKit: Manage your digitized vinyl collection with Discogs metadata."""
    ctx.obj = load_config()


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
            try:
                display_name = f.path.relative_to(scan_path)
            except ValueError:
                display_name = f.path.name

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
@click.option("--format", "fmt_filter", type=str, help="Filter search by format (e.g. Vinyl, CD).")
@click.option("--auto-move", is_flag=True, help="Automatically move files without confirmation.")
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
            # If we are using the default recordings folder, assume we want to rename/move to library
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
                            f"[yellow]No results found for query/filters.[/yellow]"
                        )
                        current_query = None  # Reset to prompt again
                        current_artist = None
                        current_album = None
                        continue

                    page_size = config.search_page_size
                    offset = 0
                    selected_release_id = None
                    break_search_loop = False

                    while offset < len(all_results):
                        page_results = all_results[offset : offset + page_size]
                        table = Table(
                            title=f"\nSearch Results for: [bold cyan]{current_query or current_artist or current_album}[/bold cyan] (Page {offset // page_size + 1})"
                        )
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
                            else:
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
            console.print(
                f"Loaded Release: [bold]{', '.join(release.artists)} - {release.title}[/bold] ({release.year})"
            )

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
                                except Exception as e:
                                    console.print(
                                        f"[yellow]Warning: Failed to download additional artwork: {e}[/yellow]"
                                    )
                except Exception as e:
                    console.print(
                        f"[yellow]Warning: Failed to download artwork: {e}[/yellow]"
                    )

            # Collect audio files
            audio_files = sorted(
                [
                    p
                    for p in path.iterdir()
                    if p.is_file() and p.suffix.lower() in (".mp3", ".flac")
                ]
            )

            if not audio_files:
                console.print(
                    f"[yellow]No supported audio files (MP3/FLAC) found in {path}.[/yellow]"
                )
                continue

            if len(audio_files) != len(release.tracklist):
                console.print(
                    f"[yellow]Warning: Found {len(audio_files)} files but release has {len(release.tracklist)} tracks.[/yellow]"
                )
                if not click.confirm("Proceed anyway?"):
                    continue

            # Tagging execution
            tagged_paths = []
            with console.status("[bold green]Tagging files...") as status:
                for i, file_path in enumerate(audio_files):
                    if i >= len(release.tracklist):
                        break

                    # Backup if enabled
                    if config.backup_enabled and config.backup_dir and not dry_run:
                        try:
                            backup_file(file_path, config.backup_dir)
                        except Exception as e:
                            console.print(
                                f"[yellow]Warning: Failed to backup {file_path.name}: {e}[/yellow]"
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
                        for img_data in all_images_data:
                            save_artwork(
                                path,
                                img_data,
                                is_primary=False,
                                subdir=config.artwork_subdir,
                            )

            if dry_run:
                console.print(
                    f"\n[bold yellow]Dry-run complete for {path.name}. No files were modified.[/bold yellow]"
                )
            else:
                console.print(
                    f"\n[bold green]Successfully tagged all files in {path.name}![/bold green]"
                )

                # Optional Renaming
                if do_rename:
                    console.print(
                        f"\n[bold blue]Renaming files in {path.name}...[/bold blue]"
                    )
                    moves = []
                    dir_moves = []
                    for i, source in enumerate(tagged_paths):
                        target = generate_path(
                            lib_root, config.naming_pattern, release, i, source.suffix
                        )
                        moves.append((source, target))

                        try:
                            display_target = target.relative_to(lib_root)
                        except ValueError:
                            display_target = target
                        console.print(
                            f"[cyan]{source.name}[/cyan] -> [green]{display_target}[/green]"
                        )

                    # Also move info file if it exists
                    info_file = path / config.info_filename
                    if info_file.exists() and moves:
                        info_target = moves[0][1].parent / config.info_filename
                        if info_file != info_target:
                            moves.append((info_file, info_target))
                            try:
                                display_info_target = info_target.relative_to(lib_root)
                            except ValueError:
                                display_info_target = info_target
                            console.print(
                                f"[cyan]{info_file.name}[/cyan] -> [green]{display_info_target}[/green]"
                            )

                    # Also move artwork file if it exists
                    artwork_file = path / config.artwork_filename
                    if artwork_file.exists() and moves:
                        artwork_target = moves[0][1].parent / config.artwork_filename
                        if artwork_file != artwork_target:
                            moves.append((artwork_file, artwork_target))
                            try:
                                display_artwork_target = artwork_target.relative_to(
                                    lib_root
                                )
                            except ValueError:
                                display_artwork_target = artwork_target
                            console.print(
                                f"[cyan]{artwork_file.name}[/cyan] -> [green]{display_artwork_target}[/green]"
                            )

                    # Also move artwork subdirectory if it exists
                    artwork_subdir = path / config.artwork_subdir
                    if artwork_subdir.exists() and artwork_subdir.is_dir() and moves:
                        artwork_subdir_target = (
                            moves[0][1].parent / config.artwork_subdir
                        )
                        if artwork_subdir != artwork_subdir_target:
                            dir_moves.append((artwork_subdir, artwork_subdir_target))
                            try:
                                display_artwork_subdir_target = (
                                    artwork_subdir_target.relative_to(lib_root)
                                )
                            except ValueError:
                                display_artwork_subdir_target = artwork_subdir_target
                            console.print(
                                f"[cyan]{artwork_subdir.name}/[/cyan] -> [green]{display_artwork_subdir_target}/[/green]"
                            )

                    if dry_run:
                        console.print(
                            "\n[bold yellow]Dry-run: Use without --dry-run to apply renaming.[/bold yellow]"
                        )
                    elif auto_move or config.auto_move or click.confirm("\nProceed with moving files?"):
                        for src, dst in moves:
                            move_file(src, dst, dry_run=False)
                        for src, dst in dir_moves:
                            move_directory(src, dst, dry_run=False)
                        console.print(
                            "\n[bold green]Files moved successfully.[/bold green]"
                        )

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
            audio_files = sorted(
                [
                    p
                    for p in path.iterdir()
                    if p.is_file() and p.suffix.lower() in (".mp3", ".flac")
                ]
            )

            if not audio_files:
                console.print(f"[yellow]No audio files found in {path.name}.[/yellow]")
                continue

            moves = []
            for i, source in enumerate(audio_files):
                if i >= len(release.tracklist):
                    break
                target = generate_path(
                    lib_root, config.naming_pattern, release, i, source.suffix
                )
                moves.append((source, target))

                # Show relative target path for readability
                try:
                    display_target = target.relative_to(lib_root)
                except ValueError:
                    display_target = target

                console.print(
                    f"[cyan]{source.name}[/cyan] -> [green]{display_target}[/green]"
                )

            # Also move info file if it exists
            info_file = path / config.info_filename
            if info_file.exists() and moves:
                info_target = moves[0][1].parent / config.info_filename
                if info_file != info_target:
                    moves.append((info_file, info_target))
                    try:
                        display_info_target = info_target.relative_to(lib_root)
                    except ValueError:
                        display_info_target = info_target
                    console.print(
                        f"[cyan]{info_file.name}[/cyan] -> [green]{display_info_target}[/green]"
                    )

            # Also move artwork file if it exists
            artwork_file = path / config.artwork_filename
            if artwork_file.exists() and moves:
                artwork_target = moves[0][1].parent / config.artwork_filename
                if artwork_file != artwork_target:
                    moves.append((artwork_file, artwork_target))
                    try:
                        display_artwork_target = artwork_target.relative_to(lib_root)
                    except ValueError:
                        display_artwork_target = artwork_target
                    console.print(
                        f"[cyan]{artwork_file.name}[/cyan] -> [green]{display_artwork_target}[/green]"
                    )

            # Also move artwork subdirectory if it exists
            dir_moves = []
            artwork_subdir = path / config.artwork_subdir
            if artwork_subdir.exists() and artwork_subdir.is_dir() and moves:
                artwork_subdir_target = moves[0][1].parent / config.artwork_subdir
                if artwork_subdir != artwork_subdir_target:
                    dir_moves.append((artwork_subdir, artwork_subdir_target))
                    try:
                        display_artwork_subdir_target = (
                            artwork_subdir_target.relative_to(lib_root)
                        )
                    except ValueError:
                        display_artwork_subdir_target = artwork_subdir_target
                    console.print(
                        f"[cyan]{artwork_subdir.name}/[/cyan] -> [green]{display_artwork_subdir_target}/[/green]"
                    )

            if dry_run:
                console.print(
                    f"\n[bold yellow]Dry-run for {path.name}: Use --commit to apply these changes.[/bold yellow]"
                )
                continue

            if click.confirm(f"\nProceed with moving files in {path.name}?"):
                for src, dst in moves:
                    move_file(src, dst, dry_run=False)
                for src, dst in dir_moves:
                    move_directory(src, dst, dry_run=False)
                console.print(
                    f"\n[bold green]Files in {path.name} moved successfully.[/bold green]"
                )

        except VinylkitError as e:
            console.print(f"[bold red]Rename failed for {path.name}:[/bold red] {e}")


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
            "[bold red]Error:[/bold red] You must set your own [bold]consumer_key[/bold] and [bold]consumer_secret[/bold] before logging in."
        )
        console.print(
            "See the [bold]Authentication Guide (auth.md)[/bold] for instructions."
        )
        return

    client = get_client(config)

    try:
        url, req_token, req_token_secret = client.get_authorize_url()
        console.print(
            f"\n1. Please visit this URL to authorize VinylKit:\n[link={url}]{url}[/link]\n"
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

        if filepath.exists():
            if not click.confirm(
                f"[yellow]Warning: {filename} already exists. Overwrite?[/yellow]",
                default=False,
            ):
                console.print("[yellow]Download aborted.[/yellow]")
                return

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(
                ["release_id", "Catalog#", "Artist", "Title", "Label", "Format", "Released"]
            )

            for r in releases:
                basic = r.get("basic_information", {})
                release_id = r.get("id")
                
                # Extract fields safely
                artists = ", ".join([a.get("name", "Unknown") for a in basic.get("artists", [])])
                title = basic.get("title", "Unknown")
                year = basic.get("year", "N/A")
                
                # Labels
                labels = basic.get("labels", [])
                label_name = labels[0].get("name", "N/A") if labels else "N/A"
                catno = labels[0].get("catno", "N/A") if labels else "N/A"
                
                # Formats
                formats = basic.get("formats", [])
                fmt_str = formats[0].get("name", "N/A") if formats else "N/A"

                writer.writerow([release_id, catno, artists, title, label_name, fmt_str, year])

        console.print(f"[bold green]Success![/bold green] Collection saved to [cyan]{filename}[/cyan]")
        console.print(f"Total releases: {len(releases)}")

    except Exception as e:
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

    console.print(f"[bold]Config Path:[/bold] {path}")
    console.print(f"[bold]Library Root:[/bold] {config_obj.library_root}")
    console.print(
        f"[bold]Recordings Root:[/bold] {config_obj.recordings_root or 'Not Set'}"
    )
    console.print(f"[bold]Auth Mode:[/bold] {config_obj.auth_mode.value}")
    console.print(f"[bold]Tag Mode:[/bold] {config_obj.tag_mode.value}")
    console.print(f"[bold]Track Numbering:[/bold] {config_obj.track_numbering.value}")
    console.print(f"[bold]Disc Mapping:[/bold] {config_obj.disc_mapping.value}")
    console.print(
        f"[bold]Consumer Key:[/bold] {'****' if config_obj.consumer_key else 'Not Set'}"
    )

    console.print(f"[bold]Naming Pattern:[/bold] {config_obj.naming_pattern}")
    console.print(f"[bold]Info Filename:[/bold] {config_obj.info_filename}")
    console.print(f"[bold]Artwork Filename:[/bold] {config_obj.artwork_filename}")
    console.print(f"[bold]Search Page Size:[/bold] {config_obj.search_page_size}")
    console.print(
        f"[bold]Default Format:[/bold] {', '.join(config_obj.default_format) if config_obj.default_format else 'None'}"
    )
    console.print(f"[bold]Auto Move:[/bold] {config_obj.auto_move}")
    console.print(f"[bold]Image Handling:[/bold] {config_obj.image_handling.value}")
    
    console.print(f"[bold]Collect All Artwork:[/bold] {config_obj.collect_all_artwork}")
    console.print(f"[bold]Artwork Subdir:[/bold] {config_obj.artwork_subdir}")
    console.print(f"[bold]Backup Enabled:[/bold] {config_obj.backup_enabled}")
    if config_obj.backup_dir:
        console.print(f"[bold]Backup Dir:[/bold] {config_obj.backup_dir}")
    console.print(
        f"[bold]Discogs Token:[/bold] {'****' if config_obj.discogs_token else 'Not Set'}"
    )


@config.command(name="set")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def config_set(config_obj: AppConfig, key: str, value: str) -> None:
    """Set a configuration value."""
    # Convert types as needed
    new_data = {
        "library_root": config_obj.library_root,
        "recordings_root": config_obj.recordings_root,
        "consumer_key": config_obj.consumer_key,
        "consumer_secret": config_obj.consumer_secret,
        "discogs_token": config_obj.discogs_token,
        "discogs_secret": config_obj.discogs_secret,
        "auth_mode": config_obj.auth_mode,
        "tag_mode": config_obj.tag_mode,
        "track_numbering": config_obj.track_numbering,
        "disc_mapping": config_obj.disc_mapping,
        "naming_pattern": config_obj.naming_pattern,
        "image_handling": config_obj.image_handling,
        "collect_all_artwork": config_obj.collect_all_artwork,
        "artwork_subdir": config_obj.artwork_subdir,
        "backup_enabled": config_obj.backup_enabled,
        "backup_dir": config_obj.backup_dir,
        "info_filename": config_obj.info_filename,
        "artwork_filename": config_obj.artwork_filename,
        "search_page_size": config_obj.search_page_size,
        "default_format": config_obj.default_format,
        "auto_move": config_obj.auto_move,
    }

    if key == "library_root":
        new_data["library_root"] = Path(value)
    elif key == "recordings_root":
        new_data["recordings_root"] = Path(value)
    elif key == "auth_mode":
        new_data["auth_mode"] = AuthMode(value)
    elif key == "tag_mode":
        new_data["tag_mode"] = TagMode(value)
    elif key == "track_numbering":
        from vinylkit.models import TrackNumbering

        new_data["track_numbering"] = TrackNumbering(value)
    elif key == "disc_mapping":
        from vinylkit.models import DiscMapping

        new_data["disc_mapping"] = DiscMapping(value)
    elif key == "consumer_key":
        new_data["consumer_key"] = value
    elif key == "consumer_secret":
        new_data["consumer_secret"] = value
    elif key == "discogs_token":
        new_data["discogs_token"] = value
    elif key == "naming_pattern":
        new_data["naming_pattern"] = value
    elif key == "image_handling":
        new_data["image_handling"] = ImageHandling(value)
    elif key == "collect_all_artwork":
        new_data["collect_all_artwork"] = value.lower() == "true"
    elif key == "artwork_subdir":
        new_data["artwork_subdir"] = value
    elif key == "backup_enabled":
        new_data["backup_enabled"] = value.lower() == "true"
    elif key == "backup_dir":
        new_data["backup_dir"] = Path(value)
    elif key == "info_filename":
        new_data["info_filename"] = value
    elif key == "artwork_filename":
        new_data["artwork_filename"] = value
    elif key == "search_page_size":
        new_data["search_page_size"] = int(value)
    elif key == "default_format":
        if value.lower() == "none":
            new_data["default_format"] = []
        else:
            new_data["default_format"] = [v.strip() for v in value.split(",")]
    elif key == "auto_move":
        new_data["auto_move"] = value.lower() == "true"
    else:
        console.print(f"[red]Unknown configuration key: {key}[/red]")
        return

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
        logging.exception("An unexpected error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
