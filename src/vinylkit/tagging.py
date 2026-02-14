from __future__ import annotations

import re
from pathlib import Path  # noqa: TC003

from loguru import logger
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.id3._frames import (
    APIC,
    TALB,
    TCON,
    TDRC,
    TIT2,
    TPE1,
    TPOS,
    TPUB,
    TRCK,
    TXXX,
)
from mutagen.mp3 import MP3

from vinylkit.exceptions import TaggingError
from vinylkit.models import (
    AudioFile,
    DiscMapping,
    DiscogsRelease,
    TagMode,
    TagStatus,
    TrackNumbering,
)

FRONT_COVER_TYPE = 3  # ID3/FLAC picture type for front cover


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
        fmt_lines = []

        for f in release.formats:
            desc = f" ({', '.join(f.descriptions)})" if f.descriptions else ""

            fmt_lines.append(f"{f.qty}x {f.name}{desc}")

        lines.append(f"{'Format:':<14} {', '.join(fmt_lines)}")

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

        logger.info(f"Created info file: {target.name}")

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
        logger.info(f"Saved artwork: {target.name}")
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
        audio = MP3(path)
        if audio.tags is None:
            return

        if preserve_artwork:
            # Keep only APIC frames
            pics = audio.tags.getall("APIC")
            audio.delete()
            audio.save()
            # Restore pics
            audio = MP3(path)
            if audio.tags is None:
                audio.add_tags()
            for p in pics:
                audio.tags.add(p)
            audio.save()
        else:
            audio.delete()
            audio.save()
    elif ext == ".flac":
        audio = FLAC(path)
        if preserve_artwork:
            pics = audio.pictures
            audio.delete()
            audio.save()
            # Restore pics
            audio = FLAC(path)
            for p in pics:
                audio.add_picture(p)
            audio.save()
        else:
            audio.delete()
            audio.save()


def get_track_number(path: Path) -> str | None:
    """Extract track number from file tags."""
    ext = path.suffix.lower()
    try:
        if ext == ".mp3":
            audio = MP3(path)
            if audio.tags and "TRCK" in audio.tags:
                # TRCK can be "1", "1/10", etc.
                val = str(audio.tags["TRCK"])
                return val.split("/")[0]
        elif ext == ".flac":
            audio = FLAC(path)
            if "tracknumber" in audio:
                val = str(audio["tracknumber"][0])
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
            )
        else:
            raise TaggingError(f"Unsupported file format: {ext}")

        logger.info(f"Tagged {path.name} successfully.")
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


def _tag_mp3(
    path: Path,
    release: DiscogsRelease,
    track_index: int,
    artwork_data: bytes | None = None,
    tag_mode: TagMode = TagMode.REPLACE,
    track_numbering: TrackNumbering = TrackNumbering.NUMERIC,
    disc_mapping: DiscMapping = DiscMapping.PHYSICAL,
) -> None:
    audio = MP3(path)

    if tag_mode == TagMode.REPLACE:
        audio.delete()
        audio.save()
        # Re-load after delete
        audio = MP3(path)

    if audio.tags is None:
        audio.add_tags()

    tags = audio.tags
    assert isinstance(tags, ID3)

    track = release.tracklist[track_index]
    track_num, disc_num = calculate_track_and_disc(
        release, track_index, track_numbering, disc_mapping
    )

    # Standard frames
    tags.add(TPE1(encoding=3, text=", ".join(release.artists)))
    tags.add(TIT2(encoding=3, text=track.title))
    tags.add(TALB(encoding=3, text=release.title))
    if release.year:
        tags.add(TDRC(encoding=3, text=str(release.year)))
    tags.add(TRCK(encoding=3, text=track_num))
    tags.add(TPOS(encoding=3, text=disc_num))
    if release.label:
        tags.add(TPUB(encoding=3, text=release.label))

    if release.genres:
        tags.add(TCON(encoding=3, text=", ".join(release.genres)))

    if release.styles:
        tags.add(TXXX(encoding=3, desc="STYLE", text=", ".join(release.styles)))

    # Custom vinyl frames
    tags.add(TXXX(encoding=3, desc="DISCOGS_POSITION", text=track.position))
    if release.catno:
        tags.add(TXXX(encoding=3, desc="CATALOGNUMBER", text=release.catno))
    if track.side:
        tags.add(TXXX(encoding=3, desc="SIDE", text=track.side))

    # Extended Discogs Tags
    if release.uri:
        tags.add(TXXX(encoding=3, desc="DISCOGS_RELEASE_URL", text=release.uri))

    if release.labels:
        labels_str = ", ".join(lbl.name for lbl in release.labels)
        tags.add(TXXX(encoding=3, desc="LABEL", text=labels_str))
        catnos_str = ", ".join(lbl.catno for lbl in release.labels if lbl.catno)
        if catnos_str:
            tags.add(TXXX(encoding=3, desc="CATALOGNUMBER", text=catnos_str))

    if release.formats:
        fmt_strs = []
        for f in release.formats:
            desc = f" ({', '.join(f.descriptions)})" if f.descriptions else ""
            fmt_strs.append(f"{f.qty}x {f.name}{desc}")
        tags.add(TXXX(encoding=3, desc="FORMAT", text=", ".join(fmt_strs)))

    if release.companies:
        comp_str = ", ".join(
            f"{c.entity_type_name}: {c.name}" for c in release.companies
        )
        tags.add(TXXX(encoding=3, desc="COMPANIES", text=comp_str))

    if release.extraartists:
        credits_str = ", ".join(f"{a.role}: {a.name}" for a in release.extraartists)
        tags.add(TXXX(encoding=3, desc="CREDITS", text=credits_str))

    if release.identifiers:
        barcodes = [i.value for i in release.identifiers if i.type == "Barcode"]
        if barcodes:
            tags.add(TXXX(encoding=3, desc="BARCODE", text=", ".join(barcodes)))

    if artwork_data:
        # In replace mode, we already deleted all APIC frames.
        # In merge mode, we might want to preserve them,
        # but usually we want to replace the cover.
        # mutagen tags.add replaces existing frames of same type/desc.
        tags.add(
            APIC(
                encoding=3,
                mime="image/jpeg",
                type=FRONT_COVER_TYPE,
                desc="Cover",
                data=artwork_data,
            )
        )

    audio.save()


def _tag_flac(
    path: Path,
    release: DiscogsRelease,
    track_index: int,
    artwork_data: bytes | None = None,
    tag_mode: TagMode = TagMode.REPLACE,
    track_numbering: TrackNumbering = TrackNumbering.NUMERIC,
    disc_mapping: DiscMapping = DiscMapping.PHYSICAL,
) -> None:
    audio = FLAC(path)

    if tag_mode == TagMode.REPLACE:
        audio.delete()
        audio.save()
        # Re-load after delete
        audio = FLAC(path)

    track = release.tracklist[track_index]
    track_num, disc_num = calculate_track_and_disc(
        release, track_index, track_numbering, disc_mapping
    )

    audio["artist"] = release.artists
    audio["title"] = track.title
    audio["album"] = release.title
    if release.year:
        audio["date"] = str(release.year)
    audio["tracknumber"] = track_num
    audio["discnumber"] = disc_num
    if release.label:
        audio["organization"] = release.label

    if release.genres:
        audio["genre"] = release.genres

    if release.styles:
        audio["style"] = release.styles

    # Custom vinyl frames
    audio["discogs_position"] = track.position
    if release.catno:
        audio["catalognumber"] = release.catno
    if track.side:
        audio["side"] = track.side

    # Extended Discogs Tags
    if release.uri:
        audio["discogs_release_url"] = release.uri

    if release.labels:
        audio["label"] = [lbl.name for lbl in release.labels]
        catnos = [lbl.catno for lbl in release.labels if lbl.catno]
        if catnos:
            audio["catalognumber"] = catnos

    if release.formats:
        fmt_strs = []
        for f in release.formats:
            desc = f" ({', '.join(f.descriptions)})" if f.descriptions else ""
            fmt_strs.append(f"{f.qty}x {f.name}{desc}")
        audio["format"] = ", ".join(fmt_strs)

    if release.companies:
        audio["companies"] = [
            f"{c.entity_type_name}: {c.name}" for c in release.companies
        ]

    if release.extraartists:
        audio["credits"] = [f"{a.role}: {a.name}" for a in release.extraartists]

    if release.identifiers:
        barcodes = [i.value for i in release.identifiers if i.type == "Barcode"]
        if barcodes:
            audio["barcode"] = barcodes

    if artwork_data:
        # For FLAC, delete existing pictures if in REPLACE mode
        # (already done by audio.delete()).
        # Or if we just want one primary picture.
        pic = Picture()
        pic.data = artwork_data
        pic.type = FRONT_COVER_TYPE
        pic.mime = "image/jpeg"
        pic.desc = "Cover"
        audio.add_picture(pic)

    audio.save()
