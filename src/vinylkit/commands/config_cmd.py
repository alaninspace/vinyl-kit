"""config group: show, set commands and converter registry."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING, Any

import rich_click as click
from rich.text import Text

from vinylkit import __version__, ui
from vinylkit.commands._helpers import console
from vinylkit.config import get_config_path, save_config
from vinylkit.models import (
    ANVHandling,
    AppConfig,
    AuthMode,
    DiscMapping,
    ImageHandling,
    TagMode,
    TrackNumbering,
)

if TYPE_CHECKING:
    from collections.abc import Callable


_NOT_SET = Text("Not Set", style="dim")
_DEFAULT = Text("Default", style="dim")


@click.group(name="config")
def config_group() -> None:
    """Manage configuration (show, set, override).

    View your current settings with 'config show', update values
    with 'config set KEY VALUE', or manage side overrides with
    'config override set OLD NEW'. Run 'config set -h' to see all valid keys.
    """


@config_group.command(name="show")
@click.pass_obj
def config_show(config_obj: AppConfig) -> None:
    """Display the current configuration."""
    path = get_config_path()
    if not path.exists():
        ui.warning("Config file does not exist. Showing defaults.")

    ui.heading(f"VinylKit v{__version__}")
    header = Text("Config Path: ", style="dim")
    header.append(str(path))
    console.print(header, highlight=False, soft_wrap=True)

    default_fmt = (
        ", ".join(config_obj.default_format) if config_obj.default_format else "None"
    )
    key_display = "****" if config_obj.consumer_key else _NOT_SET
    token_display = "****" if config_obj.discogs_token else _NOT_SET
    pos_ov_display = (
        ", ".join(f"{k} -> {v}" for k, v in config_obj.position_overrides.items())
        if config_obj.position_overrides
        else "None"
    )

    sections: list[tuple[str, list[tuple[str, str | Text]]]] = [
        (
            "General",
            [
                ("library_root", str(config_obj.library_root)),
                (
                    "recordings_root",
                    (
                        str(config_obj.recordings_root)
                        if config_obj.recordings_root
                        else _NOT_SET
                    ),
                ),
                ("auto_move", str(config_obj.auto_move)),
            ],
        ),
        (
            "Metadata & Tagging",
            [
                ("naming_pattern", config_obj.naming_pattern),
                ("anv_handling", config_obj.anv_handling),
                ("tag_mode", config_obj.tag_mode),
                (
                    "track_numbering",
                    config_obj.track_numbering,
                ),
                ("disc_mapping", config_obj.disc_mapping),
                (
                    "normalize_discogs_duplicates",
                    str(config_obj.normalize_discogs_duplicates),
                ),
                ("position_overrides", pos_ov_display),
                ("info_filename", config_obj.info_filename),
                (
                    "info_contact_email",
                    config_obj.info_contact_email or _NOT_SET,
                ),
                (
                    "info_contact_website",
                    config_obj.info_contact_website or _NOT_SET,
                ),
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
                    config_obj.image_handling,
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
                    (str(config_obj.backup_dir) if config_obj.backup_dir else _NOT_SET),
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
                ("natural_sort", str(config_obj.natural_sort)),
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
                    (str(config_obj.log_file) if config_obj.log_file else _DEFAULT),
                ),
                ("log_rotation", config_obj.log_rotation),
                ("log_retention", str(config_obj.log_retention)),
            ],
        ),
        (
            "Authentication",
            [
                ("auth_mode", config_obj.auth_mode),
                ("discogs_token", token_display),
                ("consumer_key", key_display),
            ],
        ),
    ]

    for section_title, rows in sections:
        console.print()
        ui.print_section(
            section_title,
            [
                (key, value if isinstance(value, Text) else Text(str(value)))
                for key, value in rows
            ],
        )


def _parse_bool(value: str) -> bool:
    return value.lower() == "true"


def _parse_format_list(value: str) -> list[str]:
    if value.lower() == "none":
        return []
    return [v.strip() for v in value.split(",")]


def _parse_optional_str(value: str) -> str | None:
    """Return the trimmed value, or None for an empty string (unset)."""
    return value.strip() or None


def _parse_dict(value: str) -> dict[str, str]:
    if value.lower() in ("none", ""):
        return {}
    res = {}
    for item in value.split(","):
        if ":" in item:
            k, v = item.split(":", 1)
            res[k.strip()] = v.strip()
    return res


# Maps config keys to their type converter functions
_CONFIG_CONVERTERS: dict[str, Callable[[str], Any]] = {
    "library_root": Path,
    "recordings_root": Path,
    "auth_mode": AuthMode,
    "anv_handling": ANVHandling,
    "tag_mode": TagMode,
    "track_numbering": TrackNumbering,
    "disc_mapping": DiscMapping,
    "normalize_discogs_duplicates": _parse_bool,
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
    "info_contact_email": _parse_optional_str,
    "info_contact_website": _parse_optional_str,
    "search_page_size": int,
    "default_format": _parse_format_list,
    "natural_sort": _parse_bool,
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
    "position_overrides": _parse_dict,
}


def _build_config_set_epilog() -> str:
    """Build epilog listing valid keys from _CONFIG_CONVERTERS."""
    keys = ", ".join(sorted(_CONFIG_CONVERTERS))
    return (
        "[bold]Valid keys:[/bold]"
        f"\n\n  {keys}"
        "\n\n[bold]Examples:[/bold]"
        "\n\n  vinylkit config set library_root /music/vinyl"
        "\n\n  vinylkit config set tag_mode merge"
        "\n\n  vinylkit config set position_overrides 'THIS:A,THAT:B'"
        "\n\n  vinylkit config set info_contact_email me@example.com"
        "\n\n  vinylkit config set info_contact_website ''  (unset)"
        "\n\n  vinylkit config set naming_pattern"
        " '{artist}/{album}/{title}'"
    )


@config_group.command(name="set", epilog=_build_config_set_epilog())
@click.argument("key")
@click.argument("value")
@click.pass_obj
def config_set(config_obj: AppConfig, key: str, value: str) -> None:
    """Set a configuration value."""
    if key not in _CONFIG_CONVERTERS:
        ui.error(
            f"Unknown configuration key: {key}",
            "Run 'vinylkit config set -h' to list the valid keys.",
        )
        return

    converter = _CONFIG_CONVERTERS[key]
    new_data = {
        field: getattr(config_obj, field) for field in AppConfig.__dataclass_fields__
    }
    new_data[key] = converter(value)

    new_config = AppConfig(**new_data)
    save_config(new_config)
    ui.success(f"Set {key} to {value}")


@config_group.group(name="override")
def override_group() -> None:
    """Manage vinyl position overrides (e.g. THIS -> A, THAT -> B)."""


@override_group.command(name="set")
@click.argument("old_side")
@click.argument("new_side")
@click.pass_obj
def override_set(config_obj: AppConfig, old_side: str, new_side: str) -> None:
    """Add or update a vinyl position override (e.g. 'THIS' 'A')."""
    overrides = dict(config_obj.position_overrides)
    overrides[old_side.upper()] = new_side.upper()
    new_config = dataclasses.replace(config_obj, position_overrides=overrides)
    save_config(new_config)
    ui.success(f"Set position override: {old_side.upper()} -> {new_side.upper()}")


@override_group.command(name="remove")
@click.argument("old_side")
@click.pass_obj
def override_remove(config_obj: AppConfig, old_side: str) -> None:
    """Remove a position override."""
    overrides = dict(config_obj.position_overrides)
    key = old_side.upper()
    if key in overrides:
        del overrides[key]
        new_config = dataclasses.replace(config_obj, position_overrides=overrides)
        save_config(new_config)
        ui.success(f"Removed position override for {key}")
    else:
        ui.warning(f"No position override found for {key}")


@override_group.command(name="list")
@click.pass_obj
def override_list(config_obj: AppConfig) -> None:
    """List all current position overrides."""
    if not config_obj.position_overrides:
        ui.warning("No position overrides configured.")
        return
    ui.heading("Position Overrides")
    console.print()
    table = ui.make_table()
    table.add_column("Original Discogs Side", style="cyan")
    table.add_column("Mapped Side Letter", style="green")
    for k, v in config_obj.position_overrides.items():
        table.add_row(Text(k), Text(v))
    ui.print_table(table)


@config_group.command(name="reset")
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Reset without prompting for confirmation.",
)
def config_reset(yes: bool) -> None:
    """Reset configuration to factory defaults."""
    path = get_config_path()
    if not path.exists():
        ui.warning("No custom configuration file found. Already at factory defaults.")
        return

    if not yes and not click.confirm(
        f"Are you sure you want to delete the configuration file at {path} "
        "and reset all settings to defaults?",
        default=False,
    ):
        ui.warning("Reset cancelled.")
        return

    try:
        path.unlink()
        ui.success("Reset configuration to factory defaults.")
    except OSError as e:
        ui.error(f"Failed to delete configuration file: {e}")
