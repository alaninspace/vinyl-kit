"""migrate command."""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

import click
from loguru import logger

from vinylkit.commands import _helpers
from vinylkit.exceptions import VinylkitError
from vinylkit.models import AppConfig, ImageHandling, TagMode


def _extract_id(folder_name: str) -> int | None:
    """Extract Discogs ID from folder name pattern like '... [12345]'."""
    match = re.search(r"\[(\d+)\]$", folder_name)
    if match:
        return int(match.group(1))
    return None


@click.command()
@click.argument(
    "source",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.argument(
    "destination",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--delete",
    is_flag=True,
    help="Delete source folders after successful migration.",
)
@click.option(
    "--replace-artwork",
    is_flag=True,
    default=None,
    help="Replace existing artwork in tags (default uses config).",
)
@click.option(
    "--replace-tags",
    is_flag=True,
    default=None,
    help="Replace existing tags during migration (default uses config).",
)
@click.option(
    "--id",
    "filter_ids",
    type=str,
    help="Only migrate specific Discogs IDs (comma-separated).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Display changes without performing migration.",
)
@click.pass_obj
def migrate(
    config: AppConfig,
    source: Path,
    destination: Path,
    delete: bool,
    replace_artwork: bool | None,
    replace_tags: bool | None,
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
    do_replace_tags = (
        replace_tags if replace_tags is not None else config.replace_tags_on_migration
    )

    # Parse filter IDs if provided
    target_ids: list[int] = []
    if filter_ids:
        try:
            target_ids = [int(i.strip()) for i in filter_ids.split(",")]
        except ValueError as err:
            raise click.UsageError(
                "Invalid format for --id. Use comma-separated numbers."
            ) from err

    client = _helpers.get_client(config)
    log_file = destination / "00-Migration-Results.txt"
    log_entries: list[str] = [
        f"Migration Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Source: {source}",
        f"Destination: {destination}",
        f"Delete After: {do_delete}",
        f"Replace Artwork: {do_replace_art}",
        f"Replace Tags: {do_replace_tags}",
        "=" * 80,
        "",
    ]

    if not any(f.is_dir() for f in source.iterdir()):
        _helpers.console.print("[yellow]No folders found to migrate.[/yellow]")
        return

    processed: set[str] = set()
    completed = 0

    while True:
        remaining = sorted(
            f for f in source.iterdir() if f.is_dir() and f.name not in processed
        )
        if not remaining:
            break

        folder = remaining[0]
        total = completed + len(remaining)
        pct = round(completed / total * 100)

        _helpers.console.print(
            f"\n[bold blue]\\[{completed + 1}/{total}] "
            f"Migrating:[/bold blue] {folder.name} "
            f"[dim]({pct}%)[/dim]"
        )

        processed.add(folder.name)
        completed += 1
        rid = _extract_id(folder.name)

        if target_ids and rid is not None and rid not in target_ids:
            _helpers.console.print(
                f"[yellow]Skipping {folder.name} (ID {rid} not in filter list)[/yellow]"
            )
            continue

        while rid is None:
            choice = click.prompt(
                f"No ID found for '{folder.name}'. "
                "Enter Discogs ID, 's' to skip, or 'q' to quit",
                type=str,
            )
            if choice.lower() == "q":
                _helpers.console.print("[yellow]Migration cancelled.[/yellow]")
                return
            if choice.lower() == "s":
                log_entries.append(f"SKIPPED: {folder.name} (User skipped)")
                break
            if choice.isdigit():
                rid = int(choice)
            else:
                _helpers.console.print("[red]Invalid input.[/red]")

        if rid is None:
            continue

        try:
            _migrate_folder(
                client,
                folder,
                destination,
                config,
                rid=rid,
                do_delete=do_delete,
                do_replace_art=do_replace_art,
                do_replace_tags=do_replace_tags,
                dry_run=dry_run,
                log_entries=log_entries,
            )
        except (VinylkitError, OSError) as e:
            _helpers.console.print(f"[red]Failed to migrate {folder.name}: {e}[/red]")
            log_entries.append(f"FAILED: {folder.name} ({e})")
            log_entries.append("")

    # Append rate limit summary
    info = client.rate_limit_info
    if info.limit is not None:
        log_entries.append("=" * 80)
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
        _helpers.console.print(
            f"\n[bold green]Migration complete![/bold green] Results in {log_file.name}"
        )
    else:
        _helpers.console.print(
            "\n[bold yellow]Dry-run complete.[/bold yellow] "
            "Migration log would have been saved."
        )


def _migrate_folder(
    client: _helpers.DiscogsClient,
    folder: Path,
    destination: Path,
    config: AppConfig,
    *,
    rid: int,
    do_delete: bool,
    do_replace_art: bool,
    do_replace_tags: bool,
    dry_run: bool,
    log_entries: list[str],
) -> None:
    """Process a single folder during migration."""
    release = client.get_release(rid)
    artist_str = ", ".join(release.artists)
    logger.info(
        "=== Release: {} - {} (ID: {}) ===",
        artist_str,
        release.title,
        release.id,
    )
    audio_files = _helpers.collect_audio_files(folder)

    if not audio_files:
        _helpers.console.print(
            f"[yellow]No audio files found in {folder.name}[/yellow]"
        )
        log_entries.append(f"SKIPPED: {folder.name} (No audio files)")
        return

    mapping = _build_mapping(audio_files, release, config, folder, dry_run, log_entries)
    if mapping is None:
        return

    # Execution
    log_entries.append(f"PROCESSING: {folder.name} (ID: {rid})")
    log_entries.append(f"  Release: {', '.join(release.artists)} - {release.title}")

    planned_moves: list[tuple[Path, Path, int]] = []
    for src, idx in mapping:
        _, _ = _helpers.calculate_track_and_disc(
            release, idx, config.track_numbering, config.disc_mapping
        )
        dst = _helpers.generate_path(
            destination,
            config.naming_pattern,
            release,
            idx,
            src.suffix,
        )
        planned_moves.append((src, dst, idx))
        rel_dst = dst.relative_to(destination)
        log_entries.append(f"    {src.name} -> {rel_dst}")

    if dry_run:
        _helpers.console.print(
            "[yellow]Dry-run: Migration steps logged to memory.[/yellow]"
        )
        log_entries.append("  (Dry-run: No files were moved or modified)")
        log_entries.append("")
        return

    # Real implementation
    with _helpers.console.status(f"[green]Migrating {folder.name}..."):
        artwork_data: bytes | None = None
        all_images_data: list[bytes] = []
        if do_replace_art or config.image_handling != ImageHandling.NONE:
            artwork_data, all_images_data = _helpers.download_artwork(
                client, release, config, silent=True
            )

        for src, dst, idx in planned_moves:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

            if do_replace_tags:
                _helpers.clear_audio_tags(dst, preserve_artwork=not do_replace_art)
                _helpers.tag_audio_file(
                    dst,
                    release,
                    idx,
                    artwork_data=(artwork_data if do_replace_art else None),
                    tag_mode=TagMode.REPLACE,
                    track_numbering=config.track_numbering,
                    disc_mapping=config.disc_mapping,
                    skip_tags=frozenset(config.skip_tags),
                )

        dest_dir = planned_moves[-1][1].parent
        _helpers.save_release_files(
            dest_dir,
            release,
            artwork_data,
            all_images_data,
            config,
        )

    artwork_count = _helpers.count_artwork_saved(artwork_data, all_images_data, config)

    if do_delete:
        shutil.rmtree(folder)
        _helpers.console.print(f"[green]Migrated and deleted: {folder.name}[/green]")
    else:
        _helpers.console.print(f"[green]Migrated: {folder.name}[/green]")

    rate_str = _helpers.get_rate_limit_str(client)
    if do_replace_tags:
        summary = (
            f"  Tagged {len(planned_moves)} tracks"
            f", saved {artwork_count} artwork files"
            f"{rate_str}"
        )
    else:
        summary = (
            f"  Copied {len(planned_moves)} files"
            f", saved {artwork_count} artwork files"
            f"{rate_str}"
        )
    _helpers.console.print(summary)

    log_entries.append(
        f"  [Rate Limit] {_helpers.describe_throttle_strategy(client.rate_limit_info)}"
    )
    log_entries.append("  STATUS: Success")
    log_entries.append("")


def _build_mapping(
    audio_files: list[Path],
    release: object,
    config: AppConfig,
    folder: Path,
    dry_run: bool,
    log_entries: list[str],
) -> list[tuple[Path, int]] | None:
    """Build file-to-track mapping. Returns None to skip folder."""
    from vinylkit.models import DiscogsRelease

    assert isinstance(release, DiscogsRelease)

    pos_map: dict[str, int] = {}
    num_map: dict[str, int] = {}
    for i, t in enumerate(release.tracklist):
        pos_map[t.position.lower()] = i
        tn, _ = _helpers.calculate_track_and_disc(
            release, i, config.track_numbering, config.disc_mapping
        )
        num_map[tn] = i
        if tn.isdigit():
            num_map[str(int(tn))] = i

    tagged_map: dict[int, Path] = {}
    unmatched_tags: list[tuple[str, str]] = []

    for f in audio_files:
        tag_val = _helpers.get_track_number(f)
        if tag_val:
            tag_norm = str(int(tag_val)) if tag_val.isdigit() else tag_val
            tag_lower = tag_val.lower()

            if tag_lower in pos_map:
                tagged_map[pos_map[tag_lower]] = f
            elif tag_val in num_map:
                tagged_map[num_map[tag_val]] = f
            elif tag_norm in num_map:
                tagged_map[num_map[tag_norm]] = f
            else:
                unmatched_tags.append((f.name, tag_val))
        else:
            unmatched_tags.append((f.name, "None"))

    mapping: list[tuple[Path, int]] = []

    if len(tagged_map) == len(audio_files):
        mapping.extend((tagged_map[idx], idx) for idx in sorted(tagged_map.keys()))
    else:
        _helpers.console.print(
            f"\n[yellow]Automatic mapping failed for {folder.name}:[/yellow]"
        )
        _helpers.console.print(f"  Source files: {len(audio_files)}")
        _helpers.console.print(f"  Discogs tracks: {len(release.tracklist)}")
        if unmatched_tags:
            _helpers.console.print("  Unmatched or missing tags in source:")
            for fname, tag_val in unmatched_tags[:5]:
                _helpers.console.print(f"    - {fname} (Tag: '{tag_val}')")

        if len(audio_files) == len(release.tracklist):
            prompt = (
                f"\nFile counts match ({len(audio_files)}). "
                "Map files alphabetically to Discogs tracklist?"
            )
            if dry_run or click.confirm(prompt):
                for i, f in enumerate(audio_files):
                    mapping.append((f, i))
            else:
                msg = "User refused alphabetical mapping after auto-match failed"
                log_entries.append(f"SKIPPED: {folder.name} ({msg})")
                return None
        else:
            msg = (
                f"File count ({len(audio_files)}) mismatch with "
                f"Discogs tracks ({len(release.tracklist)})"
            )
            _helpers.console.print(f"[yellow]{msg}[/yellow]")
            log_entries.append(f"SKIPPED: {folder.name} ({msg})")
            return None

    return mapping
