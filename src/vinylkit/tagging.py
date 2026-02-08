from __future__ import annotations

import logging
from pathlib import Path

from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TPUB, TXXX, APIC, TCON
from mutagen.mp3 import MP3

from vinylkit.exceptions import TaggingError
from vinylkit.models import DiscogsRelease, AudioFile, TagStatus, TagMode

logger = logging.getLogger(__name__)


def write_release_info(path: Path, release: DiscogsRelease) -> Path:
    """
    Write a release information file (info.txt) to the folder.
    """
    target = path / "release_info.txt"
    lines = [
        f"{', '.join(release.artists)} - {release.title}",
        "=" * 40,
        f"Discogs ID: {release.id}",
        f"Label:      {release.label}",
        f"Cat#:       {release.catno}",
        f"Country:    {release.country}",
        f"Released:   {release.released or release.year}",
        f"Genre:      {', '.join(release.genres)}",
        f"Style:      {', '.join(release.styles)}",
        "",
        "Tracklist:",
    ]
    
    for t in release.tracklist:
        lines.append(f"{t.position:<5} {t.title}")
        
    if release.notes:
        lines.extend(["", "Notes:", release.notes])
        
    try:
        target.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Created info file: {target.name}")
    except Exception as e:
        logger.warning(f"Failed to create info file: {e}")
        
    return target


def scan_folder(path: Path) -> list[AudioFile]:
    """
    Recursively scan a folder for supported audio files.
    """
    results = []
    for p in path.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".mp3", ".flac"):
            # For MVP, we just detect files. 
            # Deep tag analysis would happen here.
            results.append(AudioFile(
                path=p,
                extension=p.suffix.lower(),
                tag_status=TagStatus.UNTAGGED  # Default for now
            ))
    return results


def tag_audio_file(
    path: Path,
    release: DiscogsRelease,
    track_index: int,
    dry_run: bool = False,
    artwork_data: bytes | None = None,
    tag_mode: TagMode = TagMode.REPLACE,
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
    """
    if track_index >= len(release.tracklist):
        raise TaggingError(f"Track index {track_index} out of range for release {release.id}")

    track = release.tracklist[track_index]
    ext = path.suffix.lower()

    if dry_run:
        logger.info(f"[DRY-RUN] Tagging {path.name} as {track.position} - {track.title} ({tag_mode.value})")
        if artwork_data:
            logger.info(f"[DRY-RUN] Embedding artwork ({len(artwork_data)} bytes)")
        return

    try:
        if ext == ".mp3":
            _tag_mp3(path, release, track_index, artwork_data, tag_mode)
        elif ext == ".flac":
            _tag_flac(path, release, track_index, artwork_data, tag_mode)
        else:
            raise TaggingError(f"Unsupported file format: {ext}")
        
        logger.info(f"Tagged {path.name} successfully.")
    except Exception as e:
        raise TaggingError(f"Failed to tag {path}: {e}") from e


def _tag_mp3(path: Path, release: DiscogsRelease, track_index: int, artwork_data: bytes | None = None, tag_mode: TagMode = TagMode.REPLACE) -> None:
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
    
    # Standard frames
    tags.add(TPE1(encoding=3, text=", ".join(release.artists)))
    tags.add(TIT2(encoding=3, text=track.title))
    tags.add(TALB(encoding=3, text=release.title))
    if release.year:
        tags.add(TDRC(encoding=3, text=str(release.year)))
    tags.add(TRCK(encoding=3, text=track.position))
    if release.label:
        tags.add(TPUB(encoding=3, text=release.label))
    
    if release.genres:
        tags.add(TCON(encoding=3, text=", ".join(release.genres)))
    
    if release.styles:
        tags.add(TXXX(encoding=3, description="STYLE", text=", ".join(release.styles)))
    
    # Custom vinyl frames
    if release.catno:
        tags.add(TXXX(encoding=3, description="CATALOGNUMBER", text=release.catno))
    if track.side:
        tags.add(TXXX(encoding=3, description="SIDE", text=track.side))
    
    if artwork_data:
        # In replace mode, we already deleted all APIC frames. 
        # In merge mode, we might want to preserve them, but usually we want to replace the cover.
        # mutagen tags.add replaces existing frames of same type/desc.
        tags.add(APIC(
            encoding=3,
            mime="image/jpeg",
            type=3,  # Front cover
            desc="Cover",
            data=artwork_data
        ))
    
    audio.save()


def _tag_flac(path: Path, release: DiscogsRelease, track_index: int, artwork_data: bytes | None = None, tag_mode: TagMode = TagMode.REPLACE) -> None:
    audio = FLAC(path)
    
    if tag_mode == TagMode.REPLACE:
        audio.delete()
        audio.save()
        # Re-load after delete
        audio = FLAC(path)

    track = release.tracklist[track_index]
    
    audio["artist"] = release.artists
    audio["title"] = track.title
    audio["album"] = release.title
    if release.year:
        audio["date"] = str(release.year)
    audio["tracknumber"] = track.position
    if release.label:
        audio["organization"] = release.label
    
    if release.genres:
        audio["genre"] = release.genres
    
    if release.styles:
        audio["style"] = release.styles
    
    if release.catno:
        audio["catalognumber"] = release.catno
    if track.side:
        audio["side"] = track.side
        
    if artwork_data:
        # For FLAC, delete existing pictures if in REPLACE mode (already done by audio.delete())
        # Or if we just want one primary picture.
        pic = Picture()
        pic.data = artwork_data
        pic.type = 3  # Front cover
        pic.mime = "image/jpeg"
        pic.desc = "Cover"
        audio.add_picture(pic)
        
    audio.save()
