"""cache group: list, clear commands."""

from __future__ import annotations

import json
import time

import rich_click as click
from rich.table import Table

from vinylkit.commands import _helpers


def _format_age(mtime: float) -> str:
    """Format a file modification time as a human-readable age string."""
    delta = time.time() - mtime
    if delta < 0:
        delta = 0
    minutes = delta / 60
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)}h ago"
    days = hours / 24
    if days < 14:
        return f"{int(days)}d ago"
    weeks = days / 7
    if weeks < 8:
        return f"{int(weeks)}w ago"
    months = days / 30.44
    if months < 12:
        return f"{int(months)}mo ago"
    years = days / 365.25
    return f"{int(years)}y ago"


@click.group()
def cache() -> None:
    """Manage cached API responses (list, clear).

    Discogs API responses are cached locally as JSON files.
    Use 'cache list' to see cached releases or 'cache clear'
    to remove them.
    """


@cache.command(name="list")
def cache_list() -> None:
    """List cached Discogs releases."""
    cache_dir = _helpers.get_cache_dir()
    if not cache_dir.exists():
        _helpers.console.print("[yellow]Cache directory does not exist.[/yellow]")
        return

    files = sorted(cache_dir.glob("release_*.json"))
    if not files:
        _helpers.console.print("[yellow]Cache is empty.[/yellow]")
        return

    table = Table(title="Cached Releases")
    table.add_column("ID", style="magenta", no_wrap=True)
    table.add_column("Artist", style="cyan", max_width=30, overflow="ellipsis")
    table.add_column("Album", style="green", max_width=40, overflow="ellipsis")
    table.add_column("Age", style="dim", no_wrap=True)

    count = 0
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            rid = str(data.get("id", "?"))
            artists_list = data.get("artists", [])
            artist = (
                ", ".join(a.get("name", "?") for a in artists_list)
                if artists_list
                else "Unknown"
            )
            title = data.get("title", "Unknown")
            age = _format_age(f.stat().st_mtime)
            table.add_row(rid, artist, title, age)
            count += 1
        except (OSError, json.JSONDecodeError, KeyError):
            table.add_row("?", "?", f"[red]{f.name} (corrupt)[/red]", "?")
            count += 1

    _helpers.console.print(table)
    _helpers.console.print(f"\n[bold]{count} cached release(s)[/bold]")


_CACHE_CLEAR_EPILOG = (
    "[bold]Examples:[/bold]"
    "\n\n  vinylkit cache clear --yes"
    "\n\n  vinylkit cache clear --id 19983"
)


@cache.command(name="clear", epilog=_CACHE_CLEAR_EPILOG)
@click.option(
    "--id",
    "release_id",
    type=int,
    help="Clear a single release by ID.",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def cache_clear(release_id: int | None, yes: bool) -> None:
    """Clear cached Discogs API responses."""
    cache_dir = _helpers.get_cache_dir()
    if not cache_dir.exists():
        _helpers.console.print("[yellow]Cache directory does not exist.[/yellow]")
        return

    if release_id is not None:
        target = cache_dir / f"release_{release_id}.json"
        if not target.exists():
            _helpers.console.print(
                f"[yellow]No cache entry for release {release_id}.[/yellow]"
            )
            return
        target.unlink()
        _helpers.console.print(
            f"[green]Cleared cache for release {release_id}.[/green]"
        )
        return

    files = list(cache_dir.glob("release_*.json"))
    if not files:
        _helpers.console.print("[yellow]Cache is already empty.[/yellow]")
        return

    if not yes and not click.confirm(f"Delete {len(files)} cached release(s)?"):
        _helpers.console.print("[yellow]Aborted.[/yellow]")
        return

    for f in files:
        f.unlink()
    _helpers.console.print(f"[green]Cleared {len(files)} cached release(s).[/green]")
