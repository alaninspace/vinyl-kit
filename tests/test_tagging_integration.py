"""Real audio file integration tests.

Write tags, read them back, assert correctness.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

from mutagen.flac import FLAC
from mutagen.mp3 import MP3

from vinylkit.models import (
    CompanyInfo,
    DiscMapping,
    DiscogsRelease,
    ExtraArtistInfo,
    FormatInfo,
    TagMode,
    TrackInfo,
    TrackNumbering,
)
from vinylkit.tagging import FRONT_COVER_TYPE, clear_audio_tags, tag_audio_file

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


# ---------------------------------------------------------------------------
# Artwork duplication bug-fix tests
# ---------------------------------------------------------------------------

TINY_JPEG_ALT = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x02\x00\x02\x00\x00\xff\xd9"
)


class TestFLACArtworkReplace:
    """Verify FLAC REPLACE mode handles pictures correctly."""

    def test_flac_replace_clears_existing_pictures(self, flac_file: Path) -> None:
        """Re-tagging with new artwork should produce exactly 1 picture, not 2."""
        release = _single_lp_release()
        tag_audio_file(flac_file, release, track_index=0, artwork_data=TINY_JPEG)

        assert len(FLAC(flac_file).pictures) == 1

        # Re-tag with different artwork in REPLACE mode
        tag_audio_file(
            flac_file,
            release,
            track_index=0,
            artwork_data=TINY_JPEG_ALT,
            tag_mode=TagMode.REPLACE,
        )

        audio = FLAC(flac_file)
        assert len(audio.pictures) == 1
        assert audio.pictures[0].data == TINY_JPEG_ALT

    def test_flac_replace_preserves_pictures_when_no_artwork(
        self, flac_file: Path
    ) -> None:
        """Re-tagging without artwork_data should keep existing picture."""
        release = _single_lp_release()
        tag_audio_file(flac_file, release, track_index=0, artwork_data=TINY_JPEG)

        assert len(FLAC(flac_file).pictures) == 1

        # Re-tag without artwork in REPLACE mode
        tag_audio_file(
            flac_file,
            release,
            track_index=0,
            artwork_data=None,
            tag_mode=TagMode.REPLACE,
        )

        audio = FLAC(flac_file)
        assert len(audio.pictures) == 1
        assert audio.pictures[0].data == TINY_JPEG


class TestMP3ArtworkReplace:
    """Verify MP3 REPLACE mode handles APIC frames correctly."""

    def test_mp3_replace_preserves_apic_when_no_artwork(self, mp3_file: Path) -> None:
        """Re-tagging without artwork_data should keep existing APIC frame."""
        release = _single_lp_release()
        tag_audio_file(mp3_file, release, track_index=0, artwork_data=TINY_JPEG)

        tags = MP3(mp3_file).tags
        assert tags is not None
        assert len(tags.getall("APIC")) == 1

        # Re-tag without artwork in REPLACE mode
        tag_audio_file(
            mp3_file,
            release,
            track_index=0,
            artwork_data=None,
            tag_mode=TagMode.REPLACE,
        )

        tags = MP3(mp3_file).tags
        assert tags is not None
        apic = tags.getall("APIC")
        assert len(apic) == 1
        assert apic[0].data == TINY_JPEG


class TestClearAudioTagsFLAC:
    """Verify clear_audio_tags handles FLAC pictures correctly."""

    def test_preserve_artwork_does_not_double(self, flac_file: Path) -> None:
        """clear_audio_tags(preserve_artwork=True) must not duplicate pictures."""
        release = _single_lp_release()
        tag_audio_file(flac_file, release, track_index=0, artwork_data=TINY_JPEG)

        assert len(FLAC(flac_file).pictures) == 1

        clear_audio_tags(flac_file, preserve_artwork=True)

        audio = FLAC(flac_file)
        assert len(audio.pictures) == 1
        assert audio.pictures[0].data == TINY_JPEG

    def test_remove_artwork(self, flac_file: Path) -> None:
        """clear_audio_tags(preserve_artwork=False) must remove pictures."""
        release = _single_lp_release()
        tag_audio_file(flac_file, release, track_index=0, artwork_data=TINY_JPEG)

        assert len(FLAC(flac_file).pictures) == 1

        clear_audio_tags(flac_file, preserve_artwork=False)

        audio = FLAC(flac_file)
        assert len(audio.pictures) == 0


# ---------------------------------------------------------------------------
# Helper: richly populated release for new-tag tests
# ---------------------------------------------------------------------------


def _full_release() -> DiscogsRelease:
    """Release with all new fields populated for comprehensive tag testing."""
    return DiscogsRelease(
        id=19983,
        artists=["Green Velvet"],
        title="Flash",
        year=1995,
        released="1995-06-01",
        country="US",
        tracklist=[
            TrackInfo(
                position="A1",
                title="Flash",
                side="A",
                extraartists=[
                    ExtraArtistInfo(name="Cajmere", role="Remix"),
                ],
            ),
            TrackInfo(
                position="A2",
                title="Answering Machine",
                side="A",
                extraartists=[
                    ExtraArtistInfo(name="Curtis Jones", role="Written-By"),
                ],
            ),
        ],
        genres=["Electronic"],
        styles=["Techno"],
        label="Relief Records",
        catno="RR-014",
        companies=[
            CompanyInfo(name="Relief Records Inc.", entity_type_name="Pressed By"),
            CompanyInfo(name="Cajual Songs", entity_type_name="Copyright (c)"),
        ],
        formats=[FormatInfo(name="Vinyl", qty="1", descriptions=['12"', "33 ⅓ RPM"])],
        extraartists=[
            ExtraArtistInfo(name="Curtis Jones", role="Written-By"),
            ExtraArtistInfo(name="Paul Johnson", role="Mastered By"),
        ],
        notes="Classic Chicago house.",
        uri="https://www.discogs.com/release/19983",
        master_id=5000,
        master_url="https://www.discogs.com/master/5000",
        artists_sort="Green Velvet",
        data_quality="Correct",
        format_quantity=1,
    )


# ---------------------------------------------------------------------------
# New standard tag tests
# ---------------------------------------------------------------------------


class TestNewStandardTagsMP3:
    """Verify the 7 new standard ID3 frames in MP3."""

    def test_albumartist(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TPE2"]) == "Green Velvet"

    def test_media(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TMED"]) == "Vinyl"

    def test_releasedate(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TDRL"]) == "1995-06-01"

    def test_artistsort(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TSOP"]) == "Green Velvet"

    def test_composer(self, mp3_file: Path) -> None:
        release = _full_release()
        # Track A1 has no Written-By, but release has Curtis Jones as Written-By
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TCOM"]) == "Curtis Jones"

    def test_composer_from_track_level(self, mp3_file: Path) -> None:
        release = _full_release()
        # Track A2 has Curtis Jones as Written-By at track level
        tag_audio_file(mp3_file, release, track_index=1)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert "Curtis Jones" in str(tags["TCOM"])

    def test_remixer(self, mp3_file: Path) -> None:
        release = _full_release()
        # Track A1 has Cajmere as Remix at track level
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TPE4"]) == "Cajmere"

    def test_copyright(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TCOP"]) == "Cajual Songs"


class TestNewStandardTagsFLAC:
    """Verify the 7 new standard Vorbis fields in FLAC."""

    def test_albumartist(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["albumartist"] == ["Green Velvet"]

    def test_media(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["media"] == ["Vinyl"]

    def test_releasedate(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["releasedate"] == ["1995-06-01"]

    def test_artistsort(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["artistsort"] == ["Green Velvet"]

    def test_composer(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert "Curtis Jones" in audio["composer"]

    def test_remixer(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["remixer"] == ["Cajmere"]

    def test_copyright(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["copyright"] == ["Cajual Songs"]


# ---------------------------------------------------------------------------
# New custom/DISCOGS-prefixed tag tests
# ---------------------------------------------------------------------------


class TestNewDiscogsTagsMP3:
    """Verify the 7 new custom TXXX tags in MP3."""

    def test_country(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TXXX:COUNTRY"]) == "US"

    def test_discogs_release_id(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TXXX:DISCOGS_RELEASE_ID"]) == "19983"

    def test_discogs_master_id(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TXXX:DISCOGS_MASTER_ID"]) == "5000"

    def test_discogs_master_url(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert "master/5000" in str(tags["TXXX:DISCOGS_MASTER_URL"])

    def test_discogs_notes(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TXXX:DISCOGS_NOTES"]) == "Classic Chicago house."

    def test_discogs_data_quality(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TXXX:DISCOGS_DATA_QUALITY"]) == "Correct"

    def test_discogs_format_quantity(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TXXX:DISCOGS_FORMAT_QUANTITY"]) == "1"


class TestNewDiscogsTagsFLAC:
    """Verify the 7 new custom Vorbis fields in FLAC."""

    def test_country(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["country"] == ["US"]

    def test_discogs_release_id(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["discogs_release_id"] == ["19983"]

    def test_discogs_master_id(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["discogs_master_id"] == ["5000"]

    def test_discogs_master_url(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert "master/5000" in audio["discogs_master_url"][0]

    def test_discogs_notes(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["discogs_notes"] == ["Classic Chicago house."]

    def test_discogs_data_quality(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["discogs_data_quality"] == ["Correct"]

    def test_discogs_format_quantity(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        assert audio["discogs_format_quantity"] == ["1"]


# ---------------------------------------------------------------------------
# Track-level extraartists and credits enhancement
# ---------------------------------------------------------------------------


class TestTrackLevelExtraartists:
    """Credits include both release-level and track-level extraartists."""

    def test_credits_include_track_extraartists_mp3(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(mp3_file, release, track_index=0)
        tags = MP3(mp3_file).tags
        assert tags is not None
        credits_val = str(tags["TXXX:CREDITS"])
        # Release-level credit
        assert "Paul Johnson" in credits_val
        # Track-level credit
        assert "Cajmere" in credits_val

    def test_credits_include_track_extraartists_flac(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(flac_file, release, track_index=0)
        audio = FLAC(flac_file)
        credits_val = audio["credits"]
        credits_str = ", ".join(credits_val)
        assert "Paul Johnson" in credits_str
        assert "Cajmere" in credits_str


# ---------------------------------------------------------------------------
# skip_tags filtering
# ---------------------------------------------------------------------------


class TestSkipTagsMP3:
    """Verify skip_tags prevents tags from being written (MP3)."""

    def test_skip_genre_and_style(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(
            mp3_file,
            release,
            track_index=0,
            skip_tags=frozenset({"genre", "style"}),
        )
        tags = MP3(mp3_file).tags
        assert tags is not None
        # Skipped tags should not exist
        assert "TCON" not in tags
        assert "TXXX:STYLE" not in tags
        # Other tags should still be present
        assert str(tags["TPE1"]) == "Green Velvet"

    def test_skip_artwork(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(
            mp3_file,
            release,
            track_index=0,
            artwork_data=TINY_JPEG,
            skip_tags=frozenset({"artwork"}),
        )
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert len(tags.getall("APIC")) == 0

    def test_skip_discogs_release_id(self, mp3_file: Path) -> None:
        release = _full_release()
        tag_audio_file(
            mp3_file,
            release,
            track_index=0,
            skip_tags=frozenset({"discogs_release_id"}),
        )
        tags = MP3(mp3_file).tags
        assert tags is not None
        assert "TXXX:DISCOGS_RELEASE_ID" not in tags


class TestSkipTagsFLAC:
    """Verify skip_tags prevents tags from being written (FLAC)."""

    def test_skip_genre_and_style(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(
            flac_file,
            release,
            track_index=0,
            skip_tags=frozenset({"genre", "style"}),
        )
        audio = FLAC(flac_file)
        assert "genre" not in audio
        assert "style" not in audio
        assert audio["artist"] == ["Green Velvet"]

    def test_skip_artwork(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(
            flac_file,
            release,
            track_index=0,
            artwork_data=TINY_JPEG,
            skip_tags=frozenset({"artwork"}),
        )
        audio = FLAC(flac_file)
        assert len(audio.pictures) == 0

    def test_skip_country(self, flac_file: Path) -> None:
        release = _full_release()
        tag_audio_file(
            flac_file,
            release,
            track_index=0,
            skip_tags=frozenset({"country"}),
        )
        audio = FLAC(flac_file)
        assert "country" not in audio


# ---------------------------------------------------------------------------
# PER_SIDE round-trip with side=None
# ---------------------------------------------------------------------------


class TestPerSideNullSideRoundTrip:
    def test_per_side_numbering_with_side_none_mp3(self, mp3_file: Path) -> None:
        """Round-trip: PER_SIDE with side=None writes correct track number."""
        release = DiscogsRelease(
            id=1,
            artists=["A"],
            title="T",
            tracklist=[
                TrackInfo(position="1", title="T1", side=None),
                TrackInfo(position="2", title="T2", side=None),
            ],
        )
        tag_audio_file(
            mp3_file,
            release,
            track_index=1,
            track_numbering=TrackNumbering.PER_SIDE,
        )

        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TRCK"]) == "2"


# ---------------------------------------------------------------------------
# MERGE mode union-merges classification tags
# ---------------------------------------------------------------------------


class TestMergeUnionMP3:
    """MERGE mode should union-merge genre/style, not replace them (MP3)."""

    def test_genre_union_merged(self, mp3_file: Path) -> None:
        first = DiscogsRelease(
            id=1,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="A1", title="T1")],
            genres=["Jazz"],
        )
        tag_audio_file(mp3_file, first, 0, tag_mode=TagMode.REPLACE)

        second = DiscogsRelease(
            id=2,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="1", title="T1")],
            genres=["Rock"],
        )
        tag_audio_file(mp3_file, second, 0, tag_mode=TagMode.MERGE)

        tags = MP3(mp3_file).tags
        assert tags is not None
        genre_str = str(tags["TCON"])
        assert "Jazz" in genre_str
        assert "Rock" in genre_str

    def test_genre_deduplicates(self, mp3_file: Path) -> None:
        first = DiscogsRelease(
            id=1,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="A1", title="T1")],
            genres=["Electronic"],
        )
        tag_audio_file(mp3_file, first, 0, tag_mode=TagMode.REPLACE)

        second = DiscogsRelease(
            id=2,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="1", title="T1")],
            genres=["Electronic"],
        )
        tag_audio_file(mp3_file, second, 0, tag_mode=TagMode.MERGE)

        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TCON"]) == "Electronic"

    def test_style_union_merged_txxx(self, mp3_file: Path) -> None:
        first = DiscogsRelease(
            id=1,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="A1", title="T1")],
            styles=["Techno"],
        )
        tag_audio_file(mp3_file, first, 0, tag_mode=TagMode.REPLACE)

        second = DiscogsRelease(
            id=2,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="1", title="T1")],
            styles=["House"],
        )
        tag_audio_file(mp3_file, second, 0, tag_mode=TagMode.MERGE)

        tags = MP3(mp3_file).tags
        assert tags is not None
        style_str = str(tags["TXXX:STYLE"])
        assert "Techno" in style_str
        assert "House" in style_str

    def test_artist_replaced_not_merged(self, mp3_file: Path) -> None:
        """Artist is an identity tag and should be replaced, not merged."""
        first = DiscogsRelease(
            id=1,
            artists=["Old Artist"],
            title="T",
            tracklist=[TrackInfo(position="A1", title="T1")],
        )
        tag_audio_file(mp3_file, first, 0, tag_mode=TagMode.REPLACE)

        second = DiscogsRelease(
            id=2,
            artists=["New Artist"],
            title="T",
            tracklist=[TrackInfo(position="1", title="T1")],
        )
        tag_audio_file(mp3_file, second, 0, tag_mode=TagMode.MERGE)

        tags = MP3(mp3_file).tags
        assert tags is not None
        assert str(tags["TPE1"]) == "New Artist"


class TestMergeUnionFLAC:
    """MERGE mode should union-merge genre/style, not replace them (FLAC)."""

    def test_genre_union_merged(self, flac_file: Path) -> None:
        first = DiscogsRelease(
            id=1,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="A1", title="T1")],
            genres=["Jazz"],
        )
        tag_audio_file(flac_file, first, 0, tag_mode=TagMode.REPLACE)

        second = DiscogsRelease(
            id=2,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="1", title="T1")],
            genres=["Rock"],
        )
        tag_audio_file(flac_file, second, 0, tag_mode=TagMode.MERGE)

        audio = FLAC(flac_file)
        genres = audio["genre"]
        assert "Jazz" in genres
        assert "Rock" in genres

    def test_genre_deduplicates(self, flac_file: Path) -> None:
        first = DiscogsRelease(
            id=1,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="A1", title="T1")],
            genres=["Electronic"],
        )
        tag_audio_file(flac_file, first, 0, tag_mode=TagMode.REPLACE)

        second = DiscogsRelease(
            id=2,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="1", title="T1")],
            genres=["Electronic"],
        )
        tag_audio_file(flac_file, second, 0, tag_mode=TagMode.MERGE)

        audio = FLAC(flac_file)
        assert audio["genre"] == ["Electronic"]

    def test_style_union_merged(self, flac_file: Path) -> None:
        first = DiscogsRelease(
            id=1,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="A1", title="T1")],
            styles=["Techno"],
        )
        tag_audio_file(flac_file, first, 0, tag_mode=TagMode.REPLACE)

        second = DiscogsRelease(
            id=2,
            artists=["A"],
            title="T",
            tracklist=[TrackInfo(position="1", title="T1")],
            styles=["House"],
        )
        tag_audio_file(flac_file, second, 0, tag_mode=TagMode.MERGE)

        audio = FLAC(flac_file)
        styles = audio["style"]
        assert "Techno" in styles
        assert "House" in styles

    def test_artist_replaced_not_merged(self, flac_file: Path) -> None:
        """Artist is an identity tag and should be replaced, not merged."""
        first = DiscogsRelease(
            id=1,
            artists=["Old Artist"],
            title="T",
            tracklist=[TrackInfo(position="A1", title="T1")],
        )
        tag_audio_file(flac_file, first, 0, tag_mode=TagMode.REPLACE)

        second = DiscogsRelease(
            id=2,
            artists=["New Artist"],
            title="T",
            tracklist=[TrackInfo(position="1", title="T1")],
        )
        tag_audio_file(flac_file, second, 0, tag_mode=TagMode.MERGE)

        audio = FLAC(flac_file)
        assert audio["artist"] == ["New Artist"]
