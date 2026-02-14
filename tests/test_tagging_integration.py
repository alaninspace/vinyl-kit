"""Real audio file integration tests.

Write tags, read them back, assert correctness.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

from mutagen.flac import FLAC
from mutagen.mp3 import MP3

from vinylkit.models import (
    DiscMapping,
    DiscogsRelease,
    TagMode,
    TrackInfo,
    TrackNumbering,
)
from vinylkit.tagging import FRONT_COVER_TYPE, tag_audio_file

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _single_lp_release() -> DiscogsRelease:
    """Single LP: 2 sides, 4 tracks."""
    return DiscogsRelease(
        id=19983,
        artists=["Green Velvet"],
        title="Flash",
        year=1995,
        tracklist=[
            TrackInfo(position="A1", title="Flash", side="A"),
            TrackInfo(position="A2", title="Answering Machine", side="A"),
            TrackInfo(position="B1", title="Cruise Mode", side="B"),
            TrackInfo(position="B2", title="Abduction", side="B"),
        ],
        genres=["Electronic"],
        styles=["Techno"],
        label="Relief Records",
        catno="RR-014",
    )


def _double_lp_release() -> DiscogsRelease:
    """Double LP: 4 sides, 8 tracks."""
    return DiscogsRelease(
        id=236605,
        artists=["Daft Punk"],
        title="Homework",
        year=1997,
        tracklist=[
            TrackInfo(position="A1", title="Daftendirekt", side="A"),
            TrackInfo(position="A2", title="WDPK 83.7 FM", side="A"),
            TrackInfo(position="B1", title="Revolution 909", side="B"),
            TrackInfo(position="B2", title="Da Funk", side="B"),
            TrackInfo(position="C1", title="Phoenix", side="C"),
            TrackInfo(position="C2", title="Fresh", side="C"),
            TrackInfo(position="D1", title="Around the World", side="D"),
            TrackInfo(position="D2", title="Rollin' & Scratchin'", side="D"),
        ],
        genres=["Electronic"],
        styles=["House"],
        label="Virgin",
        catno="V2821",
    )


def _multi_artist_release() -> DiscogsRelease:
    """Various-artists compilation."""
    return DiscogsRelease(
        id=99999,
        artists=["Various"],
        title="Tresor Compilation",
        year=1998,
        tracklist=[
            TrackInfo(
                position="A1",
                title="Psyche",
                side="A",
                artists=["Jeff Mills"],
            ),
            TrackInfo(
                position="B1",
                title="Spastik",
                side="B",
                artists=["Plastikman"],
            ),
        ],
        genres=["Electronic"],
        styles=["Techno"],
        label="Tresor",
    )


TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
)


# ---------------------------------------------------------------------------
# MP3 round-trip tests
# ---------------------------------------------------------------------------


class TestMP3RoundTrip:
    """Tag MP3 files and verify tags survive a write→read cycle."""

    def test_basic_single_artist(self, mp3_file: Path) -> None:
        release = _single_lp_release()
        tag_audio_file(mp3_file, release, track_index=0)

        audio = MP3(mp3_file)
        tags = audio.tags
        assert tags is not None
        assert str(tags["TPE1"]) == "Green Velvet"
        assert str(tags["TIT2"]) == "Flash"
        assert str(tags["TALB"]) == "Flash"
        assert str(tags["TDRC"]) == "1995"
        assert str(tags["TPUB"]) == "Relief Records"
        assert str(tags["TCON"]) == "Electronic"
        # Default numeric track numbering
        assert str(tags["TRCK"]) == "1"

    def test_track_numbering_original(self, mp3_file: Path) -> None:
        release = _single_lp_release()
        tag_audio_file(
            mp3_file,
            release,
            track_index=2,
            track_numbering=TrackNumbering.ORIGINAL,
        )

        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TRCK"]) == "B1"

    def test_multi_disc_physical(self, mp3_file: Path) -> None:
        release = _double_lp_release()
        # Track C1 → Disc 2 under PHYSICAL mapping
        tag_audio_file(
            mp3_file,
            release,
            track_index=4,
            disc_mapping=DiscMapping.PHYSICAL,
        )

        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TPOS"]) == "2"  # C side → disc 2

    def test_vinyl_metadata(self, mp3_file: Path) -> None:
        release = _single_lp_release()
        tag_audio_file(mp3_file, release, track_index=0)

        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TXXX:DISCOGS_POSITION"]) == "A1"
        assert str(tags["TXXX:SIDE"]) == "A"
        assert str(tags["TXXX:CATALOGNUMBER"]) == "RR-014"

    def test_artwork_embedding(self, mp3_file: Path) -> None:
        release = _single_lp_release()
        tag_audio_file(mp3_file, release, track_index=0, artwork_data=TINY_JPEG)

        tags = MP3(mp3_file).tags
        assert tags is not None
        apic_frames = tags.getall("APIC")
        assert len(apic_frames) >= 1
        pic = apic_frames[0]
        assert pic.data == TINY_JPEG
        assert pic.type == FRONT_COVER_TYPE

    def test_replace_mode_clears_old_tags(self, mp3_file: Path) -> None:
        release = _single_lp_release()
        # Write initial tags
        tag_audio_file(mp3_file, release, track_index=0)

        # Overwrite with a different release in REPLACE mode
        new_release = DiscogsRelease(
            id=2,
            artists=["New Artist"],
            title="New Album",
            year=2020,
            tracklist=[TrackInfo(position="1", title="New Track")],
            genres=["Rock"],
        )
        tag_audio_file(mp3_file, new_release, track_index=0, tag_mode=TagMode.REPLACE)

        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TPE1"]) == "New Artist"
        assert str(tags["TIT2"]) == "New Track"
        # Old genre should be gone
        assert str(tags["TCON"]) == "Rock"

    def test_merge_mode_preserves_old_tags(self, mp3_file: Path) -> None:
        release = _single_lp_release()
        tag_audio_file(mp3_file, release, track_index=0)

        # Merge new data on top
        new_release = DiscogsRelease(
            id=2,
            artists=["New Artist"],
            title="New Album",
            year=2020,
            tracklist=[TrackInfo(position="1", title="New Track")],
        )
        tag_audio_file(mp3_file, new_release, track_index=0, tag_mode=TagMode.MERGE)

        tags = MP3(mp3_file).tags
        assert tags is not None
        # New values applied
        assert str(tags["TPE1"]) == "New Artist"
        assert str(tags["TIT2"]) == "New Track"
        # Old genre preserved (merge doesn't delete)
        assert str(tags["TCON"]) == "Electronic"


# ---------------------------------------------------------------------------
# FLAC round-trip tests
# ---------------------------------------------------------------------------


class TestFLACRoundTrip:
    """Tag FLAC files and verify tags survive a write→read cycle."""

    def test_basic_single_artist(self, flac_file: Path) -> None:
        release = _single_lp_release()
        tag_audio_file(flac_file, release, track_index=0)

        audio = FLAC(flac_file)
        assert audio["artist"] == ["Green Velvet"]
        assert audio["title"] == ["Flash"]
        assert audio["album"] == ["Flash"]
        assert audio["date"] == ["1995"]
        assert audio["tracknumber"] == ["1"]
        assert audio["genre"] == ["Electronic"]
        assert audio["organization"] == ["Relief Records"]

    def test_multi_disc_physical(self, flac_file: Path) -> None:
        release = _double_lp_release()
        tag_audio_file(
            flac_file,
            release,
            track_index=4,
            disc_mapping=DiscMapping.PHYSICAL,
        )

        audio = FLAC(flac_file)
        assert audio["discnumber"] == ["2"]

    def test_vinyl_metadata(self, flac_file: Path) -> None:
        release = _single_lp_release()
        tag_audio_file(flac_file, release, track_index=0)

        audio = FLAC(flac_file)
        assert audio["discogs_position"] == ["A1"]
        assert audio["side"] == ["A"]
        assert audio["catalognumber"] == ["RR-014"]

    def test_artwork_embedding(self, flac_file: Path) -> None:
        release = _single_lp_release()
        tag_audio_file(flac_file, release, track_index=0, artwork_data=TINY_JPEG)

        audio = FLAC(flac_file)
        assert len(audio.pictures) >= 1
        pic = audio.pictures[0]
        assert pic.data == TINY_JPEG
        assert pic.type == FRONT_COVER_TYPE

    def test_replace_mode_clears_old_tags(self, flac_file: Path) -> None:
        release = _single_lp_release()
        tag_audio_file(flac_file, release, track_index=0)

        new_release = DiscogsRelease(
            id=2,
            artists=["New Artist"],
            title="New Album",
            year=2020,
            tracklist=[TrackInfo(position="1", title="New Track")],
            genres=["Rock"],
        )
        tag_audio_file(flac_file, new_release, track_index=0, tag_mode=TagMode.REPLACE)

        audio = FLAC(flac_file)
        assert audio["artist"] == ["New Artist"]
        assert audio["title"] == ["New Track"]
        assert audio["genre"] == ["Rock"]
        # Old style tag should be gone
        assert "style" not in audio

    def test_merge_mode_preserves_old_tags(self, flac_file: Path) -> None:
        release = _single_lp_release()
        tag_audio_file(flac_file, release, track_index=0)

        new_release = DiscogsRelease(
            id=2,
            artists=["New Artist"],
            title="New Album",
            year=2020,
            tracklist=[TrackInfo(position="1", title="New Track")],
        )
        tag_audio_file(flac_file, new_release, track_index=0, tag_mode=TagMode.MERGE)

        audio = FLAC(flac_file)
        assert audio["artist"] == ["New Artist"]
        assert audio["title"] == ["New Track"]
        # Genre preserved from first tagging
        assert audio["genre"] == ["Electronic"]

    def test_per_side_numbering(self, flac_file: Path) -> None:
        release = _single_lp_release()
        # B1 is track index 2, first track on side B
        tag_audio_file(
            flac_file,
            release,
            track_index=2,
            track_numbering=TrackNumbering.PER_SIDE,
            disc_mapping=DiscMapping.PER_SIDE,
        )

        audio = FLAC(flac_file)
        assert audio["tracknumber"] == ["1"]  # first on side B
        assert audio["discnumber"] == ["2"]  # B = disc 2
