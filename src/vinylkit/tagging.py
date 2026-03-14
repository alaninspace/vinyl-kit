from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path  # noqa: TC003

from loguru import logger
from mutagen import MutagenError
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


class TagName(StrEnum):
    # Standard tags
    ARTIST = "artist"
    TITLE = "title"
    ALBUM = "album"
    DATE = "date"
    TRACKNUMBER = "tracknumber"
    DISCNUMBER = "discnumber"
    PUBLISHER = "publisher"
    GENRE = "genre"
    ALBUMARTIST = "albumartist"
    MEDIA = "media"
    RELEASEDATE = "releasedate"
    ARTISTSORT = "artistsort"
    COMPOSER = "composer"
    REMIXER = "remixer"
    COPYRIGHT = "copyright"
    # Ecosystem-recognized / TXXX tags
    STYLE = "style"
    DISCOGS_POSITION = "discogs_position"
    CATALOGNUMBER = "catalognumber"
    SIDE = "side"
    DISCOGS_RELEASE_URL = "discogs_release_url"
    LABEL = "label"
    FORMAT = "format"
    COMPANIES = "companies"
    CREDITS = "credits"
    BARCODE = "barcode"
    COUNTRY = "country"
    DISCOGS_RELEASE_ID = "discogs_release_id"
    DISCOGS_MASTER_ID = "discogs_master_id"
    DISCOGS_MASTER_URL = "discogs_master_url"
    DISCOGS_NOTES = "discogs_notes"
    DISCOGS_DATA_QUALITY = "discogs_data_quality"
    DISCOGS_FORMAT_QUANTITY = "discogs_format_quantity"
    ARTWORK = "artwork"


_COMPOSER_ROLES = {"written-by", "written by", "composer", "music by", "lyrics by"}
_REMIXER_ROLES = {"remix", "remixed by", "remixer"}


def _should_write(canonical_name: TagName, skip_tags: frozenset[str]) -> bool:
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
    except (OSError, MutagenError) as e:
        logger.debug(f"Could not read track number from {path}: {e}")
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
            f" ({tag_mode})"
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
        if track.side is None:
            # No side info — fall back to global numeric indexing
            track_num = str(track_index + 1)
        else:
            # Count how many tracks before this one have the same side
            side_count = 1
            for i in range(track_index):
                if release.tracklist[i].side == track.side:
                    side_count += 1
            track_num = str(side_count)

    return track_num, disc_num


# Tags that should be union-merged (not replaced) in MERGE mode.
# These are classification/additive tags where both old and new values
# are meaningful.  Identity tags (artist, composer, remixer, copyright,
# catalognumber) are always replaced because they belong to the release.
_MERGE_UNION_TAGS = frozenset(
    {
        TagName.GENRE,
        TagName.STYLE,
        TagName.CREDITS,
        TagName.COMPANIES,
        TagName.BARCODE,
        TagName.LABEL,
    }
)


def _union_merge(existing: list[str], new: list[str]) -> list[str]:
    """Return order-preserving union of *existing* and *new* values."""
    return list(dict.fromkeys(existing + new))


# -- Lookup tables for format-specific tag writing ----------------------------

_MP3_FRAMES = {
    TagName.ARTIST: TPE1,
    TagName.TITLE: TIT2,
    TagName.ALBUM: TALB,
    TagName.DATE: TDRC,
    TagName.TRACKNUMBER: TRCK,
    TagName.DISCNUMBER: TPOS,
    TagName.PUBLISHER: TPUB,
    TagName.GENRE: TCON,
    TagName.ALBUMARTIST: TPE2,
    TagName.MEDIA: TMED,
    TagName.RELEASEDATE: TDRL,
    TagName.ARTISTSORT: TSOP,
    TagName.COMPOSER: TCOM,
    TagName.REMIXER: TPE4,
    TagName.COPYRIGHT: TCOP,
}

_MP3_TXXX = {
    TagName.STYLE: "STYLE",
    TagName.DISCOGS_POSITION: "DISCOGS_POSITION",
    TagName.CATALOGNUMBER: "CATALOGNUMBER",
    TagName.SIDE: "SIDE",
    TagName.DISCOGS_RELEASE_URL: "DISCOGS_RELEASE_URL",
    TagName.LABEL: "LABEL",
    TagName.FORMAT: "FORMAT",
    TagName.COMPANIES: "COMPANIES",
    TagName.CREDITS: "CREDITS",
    TagName.BARCODE: "BARCODE",
    TagName.COUNTRY: "COUNTRY",
    TagName.DISCOGS_RELEASE_ID: "DISCOGS_RELEASE_ID",
    TagName.DISCOGS_MASTER_ID: "DISCOGS_MASTER_ID",
    TagName.DISCOGS_MASTER_URL: "DISCOGS_MASTER_URL",
    TagName.DISCOGS_NOTES: "DISCOGS_NOTES",
    TagName.DISCOGS_DATA_QUALITY: "DISCOGS_DATA_QUALITY",
    TagName.DISCOGS_FORMAT_QUANTITY: "DISCOGS_FORMAT_QUANTITY",
}

_FLAC_KEY_OVERRIDES: dict[TagName, str] = {TagName.PUBLISHER: "organization"}


def _prepare_tags(
    release: DiscogsRelease,
    track_index: int,
    track_numbering: TrackNumbering,
    disc_mapping: DiscMapping,
    skip_tags: frozenset[str],
) -> dict[TagName, str | list[str]]:
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
    tags: dict[TagName, str | list[str]] = {}

    # --- Standard tags ---
    if ok(TagName.ARTIST, skip_tags):
        tags[TagName.ARTIST] = list(release.artists)
    if ok(TagName.TITLE, skip_tags):
        tags[TagName.TITLE] = track.title
    if ok(TagName.ALBUM, skip_tags):
        tags[TagName.ALBUM] = release.title
    if ok(TagName.DATE, skip_tags) and release.year:
        tags[TagName.DATE] = str(release.year)
    if ok(TagName.TRACKNUMBER, skip_tags):
        tags[TagName.TRACKNUMBER] = track_num
    if ok(TagName.DISCNUMBER, skip_tags):
        tags[TagName.DISCNUMBER] = disc_num
    if ok(TagName.PUBLISHER, skip_tags) and release.label:
        tags[TagName.PUBLISHER] = release.label
    if ok(TagName.GENRE, skip_tags) and release.genres:
        tags[TagName.GENRE] = list(release.genres)
    if ok(TagName.STYLE, skip_tags) and release.styles:
        tags[TagName.STYLE] = list(release.styles)

    # --- Ecosystem-recognised tags ---
    if ok(TagName.ALBUMARTIST, skip_tags):
        tags[TagName.ALBUMARTIST] = ", ".join(release.artists)
    if ok(TagName.MEDIA, skip_tags) and release.formats:
        tags[TagName.MEDIA] = release.formats[0].name
    if ok(TagName.RELEASEDATE, skip_tags) and release.released:
        tags[TagName.RELEASEDATE] = release.released
    if ok(TagName.ARTISTSORT, skip_tags) and release.artists_sort:
        tags[TagName.ARTISTSORT] = release.artists_sort

    # --- Composer / remixer ---
    if ok(TagName.COMPOSER, skip_tags):
        composers = _extract_by_role(all_extra, _COMPOSER_ROLES)
        if composers:
            tags[TagName.COMPOSER] = composers
    if ok(TagName.REMIXER, skip_tags):
        remixers = _extract_by_role(all_extra, _REMIXER_ROLES)
        if remixers:
            tags[TagName.REMIXER] = remixers

    # --- Copyright ---
    if ok(TagName.COPYRIGHT, skip_tags) and release.companies:
        copyrights = [
            c.name for c in release.companies if "Copyright" in c.entity_type_name
        ]
        if copyrights:
            tags[TagName.COPYRIGHT] = copyrights

    # --- Vinyl-specific tags ---
    if ok(TagName.DISCOGS_POSITION, skip_tags):
        tags[TagName.DISCOGS_POSITION] = track.position
    if ok(TagName.CATALOGNUMBER, skip_tags):
        catnos = (
            [lbl.catno for lbl in release.labels if lbl.catno] if release.labels else []
        )
        if catnos:
            tags[TagName.CATALOGNUMBER] = catnos
        elif release.catno:
            tags[TagName.CATALOGNUMBER] = release.catno
    if ok(TagName.SIDE, skip_tags) and track.side:
        tags[TagName.SIDE] = track.side

    # --- Extended Discogs tags ---
    if ok(TagName.DISCOGS_RELEASE_URL, skip_tags) and release.uri:
        tags[TagName.DISCOGS_RELEASE_URL] = release.uri
    if ok(TagName.LABEL, skip_tags) and release.labels:
        tags[TagName.LABEL] = [lbl.name for lbl in release.labels]
    if ok(TagName.FORMAT, skip_tags) and release.formats:
        tags[TagName.FORMAT] = _format_formats(release.formats)
    if ok(TagName.COMPANIES, skip_tags) and release.companies:
        tags[TagName.COMPANIES] = [
            f"{c.entity_type_name}: {c.name}" for c in release.companies
        ]
    if ok(TagName.CREDITS, skip_tags) and all_extra:
        tags[TagName.CREDITS] = [f"{a.role}: {a.name}" for a in all_extra]
    if ok(TagName.BARCODE, skip_tags) and release.identifiers:
        barcodes = [i.value for i in release.identifiers if i.type == "Barcode"]
        if barcodes:
            tags[TagName.BARCODE] = barcodes
    if ok(TagName.COUNTRY, skip_tags) and release.country:
        tags[TagName.COUNTRY] = release.country
    if ok(TagName.DISCOGS_RELEASE_ID, skip_tags):
        tags[TagName.DISCOGS_RELEASE_ID] = str(release.id)
    if ok(TagName.DISCOGS_MASTER_ID, skip_tags) and release.master_id is not None:
        tags[TagName.DISCOGS_MASTER_ID] = str(release.master_id)
    if ok(TagName.DISCOGS_MASTER_URL, skip_tags) and release.master_url:
        tags[TagName.DISCOGS_MASTER_URL] = release.master_url
    if ok(TagName.DISCOGS_NOTES, skip_tags) and release.notes:
        tags[TagName.DISCOGS_NOTES] = release.notes
    if ok(TagName.DISCOGS_DATA_QUALITY, skip_tags) and release.data_quality:
        tags[TagName.DISCOGS_DATA_QUALITY] = release.data_quality
    if (
        ok(TagName.DISCOGS_FORMAT_QUANTITY, skip_tags)
        and release.format_quantity is not None
    ):
        tags[TagName.DISCOGS_FORMAT_QUANTITY] = str(release.format_quantity)

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

        # In MERGE mode, union-merge classification tags with existing values
        if (
            tag_mode == TagMode.MERGE
            and isinstance(value, list)
            and name in _MERGE_UNION_TAGS
        ):
            existing_text: str | None = None
            if name in _MP3_FRAMES:
                frame_key = _MP3_FRAMES[name].__name__
                if frame_key in tags:
                    existing_text = str(tags[frame_key])
            elif name in _MP3_TXXX:
                txxx_key = f"TXXX:{_MP3_TXXX[name]}"
                if txxx_key in tags:
                    existing_text = str(tags[txxx_key])
            if existing_text:
                existing_vals = [v.strip() for v in existing_text.split(", ")]
                text = ", ".join(_union_merge(existing_vals, list(value)))

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

    if _should_write(TagName.ARTWORK, skip_tags) and artwork_data:
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

        # In MERGE mode, union-merge classification tags with existing values
        if (
            tag_mode == TagMode.MERGE
            and isinstance(value, list)
            and name in _MERGE_UNION_TAGS
            and key in audio
        ):
            audio[key] = _union_merge(list(audio[key]), list(value))
        else:
            audio[key] = value

    if _should_write(TagName.ARTWORK, skip_tags) and artwork_data:
        pic = Picture()
        pic.data = artwork_data
        pic.type = FRONT_COVER_TYPE
        pic.mime = "image/jpeg"
        pic.desc = "Cover"
        audio.add_picture(pic)

    audio.save()
