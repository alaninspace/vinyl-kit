"""Edge case tests for tagging, naming, and models."""

from __future__ import annotations

from pathlib import Path

import pytest
from mutagen.flac import FLAC
from mutagen.mp3 import MP3

from vinylkit.exceptions import TaggingError
from vinylkit.models import DiscogsRelease, TrackInfo
from vinylkit.naming import generate_path
from vinylkit.tagging import tag_audio_file


def test_track_with_no_side(mp3_file: Path) -> None:
    """Tracks with side=None should still tag correctly."""
    release = DiscogsRelease(
        id=1,
        artists=["Artist"],
        title="Album",
        tracklist=[TrackInfo(position="1", title="Track", side=None)],
    )
    tag_audio_file(mp3_file, release, track_index=0)

    tags = MP3(mp3_file).tags
    assert tags is not None
    assert str(tags["TIT2"]) == "Track"
    # No SIDE TXXX frame should be written
    assert not tags.getall("TXXX:SIDE")


def test_special_characters_in_metadata(mp3_file: Path) -> None:
    """Accents, ampersands, and slashes in artist/title should tag correctly."""
    release = DiscogsRelease(
        id=1,
        artists=["Bj\u00f6rk & Thom Yorke"],
        title="Caf\u00e9 / Cr\u00e8me",
        tracklist=[TrackInfo(position="A1", title="Na\u00efve Song")],
    )
    tag_audio_file(mp3_file, release, track_index=0)

    tags = MP3(mp3_file).tags
    assert tags is not None
    assert str(tags["TPE1"]) == "Bj\u00f6rk & Thom Yorke"
    assert str(tags["TIT2"]) == "Na\u00efve Song"
    assert str(tags["TALB"]) == "Caf\u00e9 / Cr\u00e8me"


def test_special_characters_in_filename_generation() -> None:
    """Filenames should be sanitized for OS compatibility."""
    release = DiscogsRelease(
        id=1,
        artists=["AC/DC"],
        title='Back:In "Black"',
        tracklist=[TrackInfo(position="A1", title="Hells <Bells>")],
    )
    path = generate_path(Path("/music"), "{artist}/{album}/{title}", release, 0, ".mp3")
    name = path.name
    # Should not contain illegal chars
    for ch in '<>:"/|?*':
        assert ch not in name


def test_empty_tracklist_raises() -> None:
    """Tagging with an out-of-range track index should raise TaggingError."""
    release = DiscogsRelease(
        id=1,
        artists=["A"],
        title="T",
        tracklist=[],
    )
    with pytest.raises(TaggingError, match="out of range"):
        tag_audio_file(Path("fake.mp3"), release, track_index=0)


def test_release_with_no_year(mp3_file: Path) -> None:
    """Releases with year=None should not write a TDRC frame."""
    release = DiscogsRelease(
        id=1,
        artists=["Artist"],
        title="Album",
        year=None,
        tracklist=[TrackInfo(position="A1", title="Track")],
    )
    tag_audio_file(mp3_file, release, track_index=0)

    tags = MP3(mp3_file).tags
    assert tags is not None
    assert "TDRC" not in tags


def test_release_with_no_artwork(mp3_file: Path) -> None:
    """Tagging without artwork_data should produce no APIC frames."""
    release = DiscogsRelease(
        id=1,
        artists=["Artist"],
        title="Album",
        tracklist=[TrackInfo(position="A1", title="Track")],
    )
    tag_audio_file(mp3_file, release, track_index=0, artwork_data=None)

    tags = MP3(mp3_file).tags
    assert tags is not None
    assert not tags.getall("APIC")


def test_flac_special_characters(flac_file: Path) -> None:
    """FLAC Vorbis comments should handle unicode correctly."""
    release = DiscogsRelease(
        id=1,
        artists=["\u00dcbermensch"],
        title="R\u00e4umkraft",
        tracklist=[TrackInfo(position="A1", title="St\u00fcrm")],
    )
    tag_audio_file(flac_file, release, track_index=0)

    audio = FLAC(flac_file)
    assert audio["artist"] == ["\u00dcbermensch"]
    assert audio["title"] == ["St\u00fcrm"]
