"""config group: show, set commands and converter registry."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
from rich.table import Table

from vinylkit import __version__
from vinylkit.commands._helpers import console
from vinylkit.config import get_config_path, save_config
from vinylkit.models import (
    AppConfig,
    AuthMode,
    DiscMapping,
    ImageHandling,
    TagMode,
    TrackNumbering,
)

if TYPE_CHECKING:
    from collections.abc import Callable


@click.group(name="config")
def config_group() -> None:
    """Manage configuration settings."""


@config_group.command(name="show")
@click.pass_obj
def config_show(config_obj: AppConfig) -> None:
    """Display the current configuration."""
    path = get_config_path()
    if not path.exists():
        console.print("[yellow]Config file does not exist. Showing defaults.[/yellow]")

    console.print(f"[bold]VinylKit[/bold] v{__version__}")
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
                (
                    "recordings_root",
                    str(config_obj.recordings_root or "Not Set"),
                ),
                ("auto_move", str(config_obj.auto_move)),
            ],
        ),
        (
            "Metadata & Tagging",
            [
                ("naming_pattern", config_obj.naming_pattern),
                ("tag_mode", config_obj.tag_mode.value),
                (
                    "track_numbering",
                    config_obj.track_numbering.value,
                ),
                ("disc_mapping", config_obj.disc_mapping.value),
                ("info_filename", config_obj.info_filename),
                (
                    "skip_tags",
                    (
                        ", ".join(config_obj.skip_tags)
                        if config_obj.skip_tags
                        else "None"
                    ),
                ),
            ],
        ),
        (
            "Artwork",
            [
                (
                    "image_handling",
                    config_obj.image_handling.value,
                ),
                (
                    "artwork_filename",
                    config_obj.artwork_filename,
                ),
                (
                    "collect_all_artwork",
                    str(config_obj.collect_all_artwork),
                ),
                ("artwork_subdir", config_obj.artwork_subdir),
            ],
        ),
        (
            "Safety & Backups",
            [
                (
                    "backup_enabled",
                    str(config_obj.backup_enabled),
                ),
                (
                    "backup_dir",
                    str(config_obj.backup_dir or "Not Set"),
                ),
            ],
        ),
        (
            "Search & Discovery",
            [
                (
                    "search_page_size",
                    str(config_obj.search_page_size),
                ),
                ("default_format", default_fmt),
            ],
        ),
        (
            "Cache",
            [
                (
                    "cache_enabled",
                    str(config_obj.cache_enabled),
                ),
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
                (
                    "replace_tags_on_migration",
                    str(config_obj.replace_tags_on_migration),
                ),
            ],
        ),
        (
            "Logging",
            [
                ("log_level", config_obj.log_level),
                ("log_to_file", str(config_obj.log_to_file)),
                (
                    "log_file",
                    str(config_obj.log_file or "Default"),
                ),
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
    "discogs_secret": str,
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
    "replace_tags_on_migration": _parse_bool,
    "skip_tags": _parse_format_list,
    "cache_enabled": _parse_bool,
    "log_level": str,
    "log_to_file": _parse_bool,
    "log_file": Path,
    "log_rotation": str,
    "log_retention": int,
}


@config_group.command(name="set")
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
