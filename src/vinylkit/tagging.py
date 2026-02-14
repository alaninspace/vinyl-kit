from __future__ import annotations

import re
from pathlib import Path  # noqa: TC003

from loguru import logger
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.id3._frames import (
    APIC,
    TALB,
    TCOM,
    TCON,
    TCOP,
    TDRC,
    TDRL,
    TIT2,
    TMED,
    TPE1,
    TPE2,
    TPE4,
    TPOS,
    TPUB,
    TRCK,
    TSOP,
    TXXX,
)
from mutagen.mp3 import MP3

from vinylkit.exceptions import TaggingError
from vinylkit.models import (
    AudioFile,
    DiscMapping,
    DiscogsRelease,
    ExtraArtistInfo,
    FormatInfo,
    TagMode,
    TagStatus,
    TrackNumbering,
)

FRONT_COVER_TYPE = 3  # ID3/FLAC picture type for front cover

_COMPOSER_ROLES = {"written-by", "written by", "composer", "music by", "lyrics by"}
_REMIXER_ROLES = {"remix", "remixed by", "remixer"}


def _should_write(canonical_name: str, skip_tags: frozenset[str]) -> bool:
    """Return True if the tag should be written (not in the skip list)."""
    return canonical_name not in skip_tags


def _extract_by_role(
    extraartists: list[ExtraArtistInfo], role_patterns: set[str]
) -> list[str]:
    """Extract artist names matching any of the given role patterns."""
    result: list[str] = []
    for ea in extraartists:
        role_lower = ea.role.lower()
        for pattern in role_patterns:
            if pattern in role_lower:
                result.append(ea.name)
                break
    return result


def _format_formats(formats: list[FormatInfo]) -> str:
    """Build a human-readable string describing release formats."""
    parts: list[str] = []
    for f in formats:
        desc = f" ({', '.join(f.descriptions)})" if f.descriptions else ""
        parts.append(f"{f.qty}x {f.name}{desc}")
    return ", ".join(parts)


def write_release_info(
    path: Path, release: DiscogsRelease, filename: str = "release_info.txt"
) -> Path:
    """Write a release information file (info.txt) to the folder."""

    target = path / filename

    labels_str = ", ".join(
        f"{lbl.name} ({lbl.catno})" if lbl.catno else lbl.name for lbl in release.labels
    )

    header_text = f"{', '.join(release.artists)} - {release.title}"

    header_line = "=" * len(header_text)

    lines = [
        header_line,
        header_text,
        header_line,
        "",
        "RELEASE INFORMATION",
        "-------------------",
        f"{'Discogs ID:':<14} {release.id}",
        f"{'Discogs URI:':<14} {release.uri or 'N/A'}",
        f"{'Label:':<14} {labels_str}",
        f"{'Country:':<14} {release.country or 'N/A'}",
        f"{'Released:':<14} {release.released or release.year or 'N/A'}",
        f"{'Genre:':<14} {', '.join(release.genres)}",
        f"{'Style:':<14} {', '.join(release.styles)}",
    ]

    if release.formats:
        lines.append(f"{'Format:':<14} {_format_formats(release.formats)}")

    lines.extend(
        [
            "",
            "TRACKLIST",
            "---------",
        ]
    )

    lines.extend(f"{t.position:<5} {t.title}" for t in release.tracklist)

    if release.companies:
        lines.extend(
            [
                "",
                "COMPANIES",
                "---------",
            ]
        )

        lines.extend(f"  {c.entity_type_name}: {c.name}" for c in release.companies)

    if release.extraartists:
        lines.extend(
            [
                "",
                "CREDITS",
                "-------",
            ]
        )

        lines.extend(f"  {a.role}: {a.name}" for a in release.extraartists)

    if release.identifiers:
        lines.extend(
            [
                "",
                "IDENTIFIERS",
                "-----------",
            ]
        )

        for i in release.identifiers:
            desc = f" ({i.description})" if i.description else ""

            lines.append(f"  {i.type}: {i.value}{desc}")

    if release.notes:
        lines.extend(["", "NOTES", "-----", release.notes])

    try:
        target.write_text("\n".join(lines), encoding="utf-8")

        logger.debug(f"Created info file: {target.name}")

    except OSError as e:
        logger.warning(f"Failed to create info file: {e}")

    return target


def save_artwork(
    path: Path,
    artwork_data: bytes,
    filename: str = "folder.jpg",
    is_primary: bool = True,
    subdir: str = "Artwork",
) -> Path:
    """
    Save the artwork data to a file in the specified folder.
    If is_primary is False, it saves into a subdirectory using *filename*.
    """
    if is_primary:
        target = path / filename
    else:
        artwork_dir = path / subdir
        artwork_dir.mkdir(parents=True, exist_ok=True)
        target = artwork_dir / filename

    try:
        target.write_bytes(artwork_data)
        logger.debug(f"Saved artwork: {target.name}")
    except OSError as e:
        logger.warning(f"Failed to save artwork: {e}")
    return target


def scan_folder(path: Path) -> list[AudioFile]:
    """
    Recursively scan a folder for supported audio files.
    """
    return [
        AudioFile(
            path=p,
            extension=p.suffix.lower(),
            tag_status=TagStatus.UNTAGGED,
        )
        for p in path.rglob("*")
        if p.is_file() and p.suffix.lower() in (".mp3", ".flac")
    ]


def clear_audio_tags(path: Path, preserve_artwork: bool = False) -> None:
    """Clear all tags from an audio file, optionally preserving artwork."""
    ext = path.suffix.lower()
    if ext == ".mp3":
        mp3 = MP3(path)
        if mp3.tags is None:
            return

        if preserve_artwork:
            # Keep only APIC frames
            pics = mp3.tags.getall("APIC")
            mp3.delete()
            mp3.save()
            # Restore pics
            mp3 = MP3(path)
            if mp3.tags is None:
                mp3.add_tags()
            assert mp3.tags is not None
            for p in pics:
                mp3.tags.add(p)
            mp3.save()
        else:
            mp3.delete()
            mp3.save()
    elif ext == ".flac":
        flac = FLAC(path)
        if preserve_artwork:
            # FLAC.delete() only removes Vorbis comment blocks, NOT picture
            # metadata blocks — so pictures naturally survive and no
            # save/restore cycle is needed (that would double them).
            flac.delete()
            flac.save()
        else:
            # Must clear pictures explicitly before delete() since
            # FLAC.delete() does not touch PICTURE metadata blocks.
            flac.clear_pictures()
            flac.delete()
            flac.save()


def get_track_number(path: Path) -> str | None:
    """Extract track number from file tags."""
    ext = path.suffix.lower()
    try:
        if ext == ".mp3":
            mp3 = MP3(path)
            if mp3.tags and "TRCK" in mp3.tags:
                # TRCK can be "1", "1/10", etc.
                val = str(mp3.tags["TRCK"])
                return val.split("/")[0]
        elif ext == ".flac":
            flac = FLAC(path)
            if "tracknumber" in flac:
                val = str(flac["tracknumber"][0])
                return val.split("/")[0]
    except Exception:
        pass
    return None


def tag_audio_file(
    path: Path,
    release: DiscogsRelease,
    track_index: int,
    dry_run: bool = False,
    artwork_data: bytes | None = None,
    tag_mode: TagMode = TagMode.REPLACE,
    track_numbering: TrackNumbering = TrackNumbering.NUMERIC,
    disc_mapping: DiscMapping = DiscMapping.PHYSICAL,
    skip_tags: frozenset[str] = frozenset(),
) -> None:
    """
    Tag an audio file with Discogs release metadata.

    Args:
        path: Path to the audio file.
        release: DiscogsRelease object containing metadata.
        track_index: Index of the track in the release's tracklist.
        dry_run: If True, do not write changes to disk.
        artwork_data: Binary data of the album art to embed.
        tag_mode: REPLACE (delete existing) or MERGE (keep existing).
        track_numbering: How to format track numbers.
        disc_mapping: How to map discs.
        skip_tags: Set of canonical tag names to omit.
    """
    if track_index >= len(release.tracklist):
        raise TaggingError(
            f"Track index {track_index} out of range for release {release.id}"
        )

    track = release.tracklist[track_index]
    ext = path.suffix.lower()

    if dry_run:
        logger.info(
            f"[DRY-RUN] Tagging {path.name} as"
            f" {track.position} - {track.title}"
            f" ({tag_mode.value})"
        )
        if artwork_data:
            logger.info(f"[DRY-RUN] Embedding artwork ({len(artwork_data)} bytes)")
        return

    try:
        if ext == ".mp3":
            _tag_mp3(
                path,
                release,
                track_index,
                artwork_data,
                tag_mode,
                track_numbering,
                disc_mapping,
                skip_tags,
            )
        elif ext == ".flac":
            _tag_flac(
                path,
                release,
                track_index,
                artwork_data,
                tag_mode,
                track_numbering,
                disc_mapping,
                skip_tags,
            )
        else:
            raise TaggingError(f"Unsupported file format: {ext}")

        logger.debug(f"Tagged {path.name} successfully.")
    except Exception as e:
        raise TaggingError(f"Failed to tag {path}: {e}") from e


def calculate_track_and_disc(
    release: DiscogsRelease,
    track_index: int,
    track_numbering: TrackNumbering,
    disc_mapping: DiscMapping,
) -> tuple[str, str]:
    """
    Calculate track number and disc number based on configuration.
    """
    track = release.tracklist[track_index]

    # 1. Calculate Disc Number
    disc_num = "1"
    if disc_mapping == DiscMapping.PER_SIDE:
        # A=1, B=2, C=3...
        if track.side:
            # Map A->1, B->2...
            disc_num = str(ord(track.side[0].upper()) - ord("A") + 1)
    elif disc_mapping == DiscMapping.PHYSICAL:
        # Standard Vinyl: A,B=1, C,D=2, E,F=3...
        # Also check for explicit 1A, 2A prefix
        disc_prefix_match = re.match(r"^(\d+)", track.position)
        if disc_prefix_match:
            disc_num = disc_prefix_match.group(1)
        elif track.side:
            # A, B -> 1; C, D -> 2...
            side_val = ord(track.side[0].upper()) - ord("A")
            disc_num = str((side_val // 2) + 1)
    elif disc_mapping == DiscMapping.ORIGINAL:
        # Discogs usually doesn't have a clear numeric disc count
        # in simple API responses for single releases,
        # but we'll default to 1 for now or check formats
        disc_num = "1"

    # 2. Calculate Track Number
    track_num = track.position
    if track_numbering == TrackNumbering.NUMERIC:
        track_num = str(track_index + 1)
    elif track_numbering == TrackNumbering.PER_SIDE:
        # Count how many tracks before this one have the same side
        side_count = 1
        for i in range(track_index):
            if release.tracklist[i].side == track.side:
                side_count += 1
        track_num = str(side_count)

    return track_num, disc_num


# -- Lookup tables for format-specific tag writing ----------------------------

_MP3_FRAMES = {
    "artist": TPE1,
    "title": TIT2,
    "album": TALB,
    "date": TDRC,
    "tracknumber": TRCK,
    "discnumber": TPOS,
    "publisher": TPUB,
    "genre": TCON,
    "albumartist": TPE2,
    "media": TMED,
    "releasedate": TDRL,
    "artistsort": TSOP,
    "composer": TCOM,
    "remixer": TPE4,
    "copyright": TCOP,
}

_MP3_TXXX = {
    "style": "STYLE",
    "discogs_position": "DISCOGS_POSITION",
    "catalognumber": "CATALOGNUMBER",
    "side": "SIDE",
    "discogs_release_url": "DISCOGS_RELEASE_URL",
    "label": "LABEL",
    "format": "FORMAT",
    "companies": "COMPANIES",
    "credits": "CREDITS",
    "barcode": "BARCODE",
    "country": "COUNTRY",
    "discogs_release_id": "DISCOGS_RELEASE_ID",
    "discogs_master_id": "DISCOGS_MASTER_ID",
    "discogs_master_url": "DISCOGS_MASTER_URL",
    "discogs_notes": "DISCOGS_NOTES",
    "discogs_data_quality": "DISCOGS_DATA_QUALITY",
    "discogs_format_quantity": "DISCOGS_FORMAT_QUANTITY",
}

_FLAC_KEY_OVERRIDES = {"publisher": "organization"}


def _prepare_tags(
    release: DiscogsRelease,
    track_index: int,
    track_numbering: TrackNumbering,
    disc_mapping: DiscMapping,
    skip_tags: frozenset[str],
) -> dict[str, str | list[str]]:
    """Compute all tag values (except artwork).

    Returns a dict of canonical tag name to value.  Multi-value tags
    are stored as ``list[str]``; scalar tags as ``str``.  The MP3
    writer joins lists with ``", "``; the FLAC writer stores them
    natively as multi-value Vorbis comments.
    """
    track = release.tracklist[track_index]
    track_num, disc_num = calculate_track_and_disc(
        release, track_index, track_numbering, disc_mapping
    )
    all_extra = list(release.extraartists) + list(track.extraartists)
    ok = _should_write
    tags: dict[str, str | list[str]] = {}

    # --- Standard tags ---
    if ok("artist", skip_tags):
        tags["artist"] = list(release.artists)
    if ok("title", skip_tags):
        tags["title"] = track.title
    if ok("album", skip_tags):
        tags["album"] = release.title
    if ok("date", skip_tags) and release.year:
        tags["date"] = str(release.year)
    if ok("tracknumber", skip_tags):
        tags["tracknumber"] = track_num
    if ok("discnumber", skip_tags):
        tags["discnumber"] = disc_num
    if ok("publisher", skip_tags) and release.label:
        tags["publisher"] = release.label
    if ok("genre", skip_tags) and release.genres:
        tags["genre"] = list(release.genres)
    if ok("style", skip_tags) and release.styles:
        tags["style"] = list(release.styles)

    # --- Ecosystem-recognised tags ---
    if ok("albumartist", skip_tags):
        tags["albumartist"] = ", ".join(release.artists)
    if ok("media", skip_tags) and release.formats:
        tags["media"] = release.formats[0].name
    if ok("releasedate", skip_tags) and release.released:
        tags["releasedate"] = release.released
    if ok("artistsort", skip_tags) and release.artists_sort:
        tags["artistsort"] = release.artists_sort

    # --- Composer / remixer ---
    if ok("composer", skip_tags):
        composers = _extract_by_role(all_extra, _COMPOSER_ROLES)
        if composers:
            tags["composer"] = composers
    if ok("remixer", skip_tags):
        remixers = _extract_by_role(all_extra, _REMIXER_ROLES)
        if remixers:
            tags["remixer"] = remixers

    # --- Copyright ---
    if ok("copyright", skip_tags) and release.companies:
        copyrights = [
            c.name for c in release.companies if "Copyright" in c.entity_type_name
        ]
        if copyrights:
            tags["copyright"] = copyrights

    # --- Vinyl-specific tags ---
    if ok("discogs_position", skip_tags):
        tags["discogs_position"] = track.position
    if ok("catalognumber", skip_tags):
        catnos = (
            [lbl.catno for lbl in release.labels if lbl.catno] if release.labels else []
        )
        if catnos:
            tags["catalognumber"] = catnos
        elif release.catno:
            tags["catalognumber"] = release.catno
    if ok("side", skip_tags) and track.side:
        tags["side"] = track.side

    # --- Extended Discogs tags ---
    if ok("discogs_release_url", skip_tags) and release.uri:
        tags["discogs_release_url"] = release.uri
    if ok("label", skip_tags) and release.labels:
        tags["label"] = [lbl.name for lbl in release.labels]
    if ok("format", skip_tags) and release.formats:
        tags["format"] = _format_formats(release.formats)
    if ok("companies", skip_tags) and release.companies:
        tags["companies"] = [
            f"{c.entity_type_name}: {c.name}" for c in release.companies
        ]
    if ok("credits", skip_tags) and all_extra:
        tags["credits"] = [f"{a.role}: {a.name}" for a in all_extra]
    if ok("barcode", skip_tags) and release.identifiers:
        barcodes = [i.value for i in release.identifiers if i.type == "Barcode"]
        if barcodes:
            tags["barcode"] = barcodes
    if ok("country", skip_tags) and release.country:
        tags["country"] = release.country
    if ok("discogs_release_id", skip_tags):
        tags["discogs_release_id"] = str(release.id)
    if ok("discogs_master_id", skip_tags) and release.master_id is not None:
        tags["discogs_master_id"] = str(release.master_id)
    if ok("discogs_master_url", skip_tags) and release.master_url:
        tags["discogs_master_url"] = release.master_url
    if ok("discogs_notes", skip_tags) and release.notes:
        tags["discogs_notes"] = release.notes
    if ok("discogs_data_quality", skip_tags) and release.data_quality:
        tags["discogs_data_quality"] = release.data_quality
    if ok("discogs_format_quantity", skip_tags) and release.format_quantity is not None:
        tags["discogs_format_quantity"] = str(release.format_quantity)

    return tags


def _tag_mp3(
    path: Path,
    release: DiscogsRelease,
    track_index: int,
    artwork_data: bytes | None = None,
    tag_mode: TagMode = TagMode.REPLACE,
    track_numbering: TrackNumbering = TrackNumbering.NUMERIC,
    disc_mapping: DiscMapping = DiscMapping.PHYSICAL,
    skip_tags: frozenset[str] = frozenset(),
) -> None:
    audio = MP3(path)
    saved_pics: list[APIC] = []

    if tag_mode == TagMode.REPLACE:
        # Save existing artwork if we're not replacing it
        if artwork_data is None and audio.tags is not None:
            saved_pics = audio.tags.getall("APIC")

        audio.delete()
        audio.save()
        # Re-load after delete
        audio = MP3(path)

    if audio.tags is None:
        audio.add_tags()

    tags = audio.tags
    assert isinstance(tags, ID3)

    tag_values = _prepare_tags(
        release, track_index, track_numbering, disc_mapping, skip_tags
    )

    for name, value in tag_values.items():
        text = ", ".join(value) if isinstance(value, list) else value
        if name in _MP3_FRAMES:
            tags.add(_MP3_FRAMES[name](encoding=3, text=text))
        elif name in _MP3_TXXX:
            tags.add(
                TXXX(
                    encoding=3,
                    desc=_MP3_TXXX[name],
                    text=text,
                )
            )

    if _should_write("artwork", skip_tags) and artwork_data:
        tags.add(
            APIC(
                encoding=3,
                mime="image/jpeg",
                type=FRONT_COVER_TYPE,
                desc="Cover",
                data=artwork_data,
            )
        )
    elif tag_mode == TagMode.REPLACE and saved_pics:
        # Restore previously saved artwork when not replacing it
        for p in saved_pics:
            tags.add(p)

    audio.save()


def _tag_flac(
    path: Path,
    release: DiscogsRelease,
    track_index: int,
    artwork_data: bytes | None = None,
    tag_mode: TagMode = TagMode.REPLACE,
    track_numbering: TrackNumbering = TrackNumbering.NUMERIC,
    disc_mapping: DiscMapping = DiscMapping.PHYSICAL,
    skip_tags: frozenset[str] = frozenset(),
) -> None:
    audio = FLAC(path)

    if tag_mode == TagMode.REPLACE:
        if artwork_data is not None:
            # Must clear pictures explicitly — FLAC.delete() only
            # removes Vorbis comment blocks, not PICTURE blocks.
            audio.clear_pictures()
        # When artwork_data is None, pictures survive delete()
        # naturally, preserving existing artwork.
        audio.delete()
        audio.save()
        # Re-load after delete
        audio = FLAC(path)

    tag_values = _prepare_tags(
        release, track_index, track_numbering, disc_mapping, skip_tags
    )

    for name, value in tag_values.items():
        key = _FLAC_KEY_OVERRIDES.get(name, name)
        audio[key] = value

    if _should_write("artwork", skip_tags) and artwork_data:
        pic = Picture()
        pic.data = artwork_data
        pic.type = FRONT_COVER_TYPE
        pic.mime = "image/jpeg"
        pic.desc = "Cover"
        audio.add_picture(pic)

    audio.save()
