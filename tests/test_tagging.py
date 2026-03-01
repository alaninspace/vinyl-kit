from __future__ import annotations

from pathlib import Path  # noqa: TC003

import pytest

from vinylkit.models import (
    DiscMapping,
    DiscogsRelease,
    ExtraArtistInfo,
    TrackInfo,
    TrackNumbering,
)
from vinylkit.tagging import (
    _COMPOSER_ROLES,
    _REMIXER_ROLES,
    _extract_by_role,
    _should_write,
    calculate_track_and_disc,
    get_track_number,
    tag_audio_file,
)


@pytest.fixture
def mock_mp3(tmp_path: Path) -> Path:
    p = tmp_path / "test.mp3"
    p.write_bytes(b"empty")
    return p


@pytest.fixture
def sample_release() -> DiscogsRelease:
    return DiscogsRelease(
        id=123,
        artists=["Artist Name"],
        title="Album Title",
        year=2020,
        label="Record Label",
        catno="CAT001",
        tracklist=[
            TrackInfo(position="A1", title="Track 1", side="A"),
            TrackInfo(position="A2", title="Track 2", side="A"),
        ],
    )


def test_tag_audio_file_mp3(
    mock_mp3: Path, sample_release: DiscogsRelease, mocker
) -> None:
    # Mock mutagen to avoid actual file I/O complexity in unit test
    from mutagen.id3 import ID3

    mock_mp3_class = mocker.patch("vinylkit.tagging.MP3")
    mock_audio = mock_mp3_class.return_value
    mock_audio.tags = mocker.Mock(spec=ID3)
    mock_audio.tags.getall.return_value = []

    tag_audio_file(mock_mp3, sample_release, track_index=0)

    # Verify mutagen was used
    assert mock_mp3_class.called
    assert mock_audio.save.called


def test_tag_audio_file_dry_run(
    mock_mp3: Path, sample_release: DiscogsRelease, mocker
) -> None:
    mock_mp3_class = mocker.patch("vinylkit.tagging.MP3")
    mock_audio = mock_mp3_class.return_value

    tag_audio_file(mock_mp3, sample_release, track_index=0, dry_run=True)

    # Verify mutagen was NOT used to save
    assert not mock_audio.save.called


def test_scan_folder_finds_files(tmp_path: Path) -> None:
    from vinylkit.tagging import scan_folder

    (tmp_path / "song1.mp3").write_text("data")
    (tmp_path / "song2.flac").write_text("data")
    (tmp_path / "readme.txt").write_text("data")

    files = scan_folder(tmp_path)
    assert len(files) == 2
    assert any(f.extension == ".mp3" for f in files)
    assert any(f.extension == ".flac" for f in files)


def test_calculate_track_and_disc_logic():
    from vinylkit.models import DiscMapping, TrackNumbering
    from vinylkit.tagging import calculate_track_and_disc

    release = DiscogsRelease(
        id=1,
        artists=["A"],
        title="T",
        tracklist=[
            TrackInfo(position="A1", title="T1", side="A"),
            TrackInfo(position="A2", title="T2", side="A"),
            TrackInfo(position="B1", title="T3", side="B"),
        ],
    )

    # 1. Default: Numeric tracks, single disc
    t, d = calculate_track_and_disc(
        release, 2, TrackNumbering.NUMERIC, DiscMapping.SINGLE
    )
    assert t == "3"
    assert d == "1"

    # 2. Per Side: Numeric resets, Discs 1, 2...
    t, d = calculate_track_and_disc(
        release, 2, TrackNumbering.PER_SIDE, DiscMapping.PER_SIDE
    )
    assert t == "1"  # B1 is the 1st track on side B
    assert d == "2"  # Side B is disc 2

    # 3. Original: Keep A1
    t, d = calculate_track_and_disc(
        release, 0, TrackNumbering.ORIGINAL, DiscMapping.SINGLE
    )
    assert t == "A1"
    assert d == "1"

    # 4. Physical: A,B=1, C,D=2
    # Test Side A
    t, d = calculate_track_and_disc(
        release, 1, TrackNumbering.NUMERIC, DiscMapping.PHYSICAL
    )
    assert d == "1"  # A2 -> Disc 1
    # Test Side B
    t, d = calculate_track_and_disc(
        release, 2, TrackNumbering.NUMERIC, DiscMapping.PHYSICAL
    )
    assert d == "1"  # B1 -> Disc 1

    # Test Side C
    release_2lp = DiscogsRelease(
        id=2,
        artists=["A"],
        title="T",
        tracklist=[TrackInfo(position="C1", title="T3", side="C")],
    )
    t, d = calculate_track_and_disc(
        release_2lp, 0, TrackNumbering.NUMERIC, DiscMapping.PHYSICAL
    )
    assert d == "2"  # C1 -> Disc 2

    # Test Numeric Prefix (1A, 2A)
    release_prefix = DiscogsRelease(
        id=3,
        artists=["A"],
        title="T",
        tracklist=[TrackInfo(position="1A", title="T1", side="A")],
    )
    t, d = calculate_track_and_disc(
        release_prefix, 0, TrackNumbering.NUMERIC, DiscMapping.PHYSICAL
    )
    assert d == "1"


# ---------------------------------------------------------------------------
# _should_write tests
# ---------------------------------------------------------------------------


def test_should_write_empty_skip_set() -> None:
    assert _should_write("artist", frozenset()) is True


def test_should_write_tag_in_skip_set() -> None:
    assert _should_write("artist", frozenset({"artist", "genre"})) is False


def test_should_write_tag_not_in_skip_set() -> None:
    assert _should_write("title", frozenset({"artist", "genre"})) is True


# ---------------------------------------------------------------------------
# _extract_by_role tests
# ---------------------------------------------------------------------------


def test_extract_composers() -> None:
    eas = [
        ExtraArtistInfo(name="John", role="Written-By"),
        ExtraArtistInfo(name="Paul", role="Producer"),
        ExtraArtistInfo(name="George", role="Composer"),
    ]
    result = _extract_by_role(eas, _COMPOSER_ROLES)
    assert result == ["John", "George"]


def test_extract_remixers() -> None:
    eas = [
        ExtraArtistInfo(name="DJ Shadow", role="Remix"),
        ExtraArtistInfo(name="RZA", role="Producer"),
        ExtraArtistInfo(name="Fatboy Slim", role="Remixed By"),
    ]
    result = _extract_by_role(eas, _REMIXER_ROLES)
    assert result == ["DJ Shadow", "Fatboy Slim"]


def test_extract_by_role_empty() -> None:
    assert _extract_by_role([], _COMPOSER_ROLES) == []


def test_extract_by_role_no_match() -> None:
    eas = [ExtraArtistInfo(name="Eng", role="Mastered By")]
    assert _extract_by_role(eas, _COMPOSER_ROLES) == []


def test_extract_by_role_case_insensitive() -> None:
    eas = [ExtraArtistInfo(name="Bach", role="WRITTEN-BY")]
    result = _extract_by_role(eas, _COMPOSER_ROLES)
    assert result == ["Bach"]


# ---------------------------------------------------------------------------
# get_track_number exception handling
# ---------------------------------------------------------------------------


def test_get_track_number_corrupt_mp3_returns_none(tmp_path: Path) -> None:
    """A corrupt MP3 file should return None, not raise."""
    bad = tmp_path / "corrupt.mp3"
    bad.write_bytes(b"\x00" * 100)
    assert get_track_number(bad) is None


def test_get_track_number_corrupt_flac_returns_none(tmp_path: Path) -> None:
    """A corrupt FLAC file should return None, not raise."""
    bad = tmp_path / "corrupt.flac"
    bad.write_bytes(b"\x00" * 100)
    assert get_track_number(bad) is None


def test_get_track_number_missing_file_returns_none(tmp_path: Path) -> None:
    """A non-existent file should return None (OSError caught)."""
    missing = tmp_path / "missing.mp3"
    assert get_track_number(missing) is None


def test_get_track_number_valid_mp3(mp3_file: Path) -> None:
    """A properly tagged MP3 should return the track number."""
    release = DiscogsRelease(
        id=1,
        artists=["A"],
        title="T",
        tracklist=[TrackInfo(position="A1", title="T1")],
    )
    tag_audio_file(mp3_file, release, track_index=0)
    assert get_track_number(mp3_file) == "1"


# ---------------------------------------------------------------------------
# PER_SIDE numbering with side=None fallback
# ---------------------------------------------------------------------------


def test_per_side_side_none_falls_back_to_numeric() -> None:
    """Tracks with side=None should get global numeric track numbers."""
    release = DiscogsRelease(
        id=1,
        artists=["A"],
        title="T",
        tracklist=[
            TrackInfo(position="1", title="T1", side=None),
            TrackInfo(position="2", title="T2", side=None),
            TrackInfo(position="3", title="T3", side=None),
        ],
    )

    t1, _ = calculate_track_and_disc(
        release, 0, TrackNumbering.PER_SIDE, DiscMapping.SINGLE
    )
    t2, _ = calculate_track_and_disc(
        release, 1, TrackNumbering.PER_SIDE, DiscMapping.SINGLE
    )
    t3, _ = calculate_track_and_disc(
        release, 2, TrackNumbering.PER_SIDE, DiscMapping.SINGLE
    )

    assert t1 == "1"
    assert t2 == "2"
    assert t3 == "3"


def test_per_side_mixed_side_and_none() -> None:
    """Tracks mixing side=None and real sides should number correctly."""
    release = DiscogsRelease(
        id=1,
        artists=["A"],
        title="T",
        tracklist=[
            TrackInfo(position="A1", title="T1", side="A"),
            TrackInfo(position="A2", title="T2", side="A"),
            TrackInfo(position="", title="Bonus", side=None),
        ],
    )

    t1, _ = calculate_track_and_disc(
        release, 0, TrackNumbering.PER_SIDE, DiscMapping.SINGLE
    )
    t2, _ = calculate_track_and_disc(
        release, 1, TrackNumbering.PER_SIDE, DiscMapping.SINGLE
    )
    t3, _ = calculate_track_and_disc(
        release, 2, TrackNumbering.PER_SIDE, DiscMapping.SINGLE
    )

    assert t1 == "1"
    assert t2 == "2"
    assert t3 == "3"  # global index, not "1"
