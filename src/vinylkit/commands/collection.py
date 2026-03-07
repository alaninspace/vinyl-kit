"""collection group: download command."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click
from rich.panel import Panel

from vinylkit.commands import _helpers
from vinylkit.exceptions import VinylkitError

if TYPE_CHECKING:
    from vinylkit.models import AppConfig


@click.group()
def collection() -> None:
    """Manage your Discogs collection (download).

    Export your Discogs collection data to a local CSV file
    for offline browsing or analysis.
    """


_DOWNLOAD_EPILOG = "[bold]Examples:[/bold]\n\n  vinylkit collection download"


@collection.command(name="download", epilog=_DOWNLOAD_EPILOG)
@click.pass_obj
def collection_download(config: AppConfig) -> None:
    """Download your Discogs collection to a CSV file."""
    client = _helpers.get_client(config)
    try:
        with _helpers.console.status("[bold green]Fetching identity..."):
            identity_resp = client.get_identity()
            username = identity_resp.get("username")

        if not username:
            _helpers.console.print("[red]Error: Could not determine username.[/red]")
            return

        with _helpers.console.status(
            f"[bold green]Downloading collection for {username}..."
        ):
            releases = client.get_collection_releases(username)

        if not releases:
            _helpers.console.print(
                "[yellow]No releases found in your collection.[/yellow]"
            )
            return

        date_prefix = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_prefix}_{username}_collection.csv"
        filepath = Path.cwd() / filename

        if filepath.exists() and not click.confirm(
            f"[yellow]Warning: {filename} already exists. Overwrite?[/yellow]",
            default=False,
        ):
            _helpers.console.print("[yellow]Download aborted.[/yellow]")
            return

        with filepath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
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

                artists = ", ".join(
                    a.get("name", "Unknown") for a in basic.get("artists", [])
                )
                title = basic.get("title", "Unknown")
                year = basic.get("year", "N/A")

                labels = basic.get("labels", [])
                label_name = labels[0].get("name", "N/A") if labels else "N/A"
                catno = labels[0].get("catno", "N/A") if labels else "N/A"

                formats = basic.get("formats", [])
                fmt_str = formats[0].get("name", "N/A") if formats else "N/A"

                writer.writerow(
                    [
                        release_id,
                        catno,
                        artists,
                        title,
                        label_name,
                        fmt_str,
                        year,
                    ]
                )

        _helpers.console.print()
        _helpers.console.print(
            Panel(
                f"Collection saved to [cyan]{filename}[/cyan]"
                f"\nTotal releases: [bold]{len(releases)}[/bold]",
                title="[bold green]Success![/bold green]",
                expand=False,
                border_style="green",
            )
        )

    except (VinylkitError, OSError) as e:
        _helpers.console.print(
            f"[bold red]Failed to download collection:[/bold red] {e}"
        )
