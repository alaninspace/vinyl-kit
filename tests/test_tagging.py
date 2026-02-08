from __future__ import annotations

from pathlib import Path

import pytest

from vinylkit.models import DiscogsRelease, TrackInfo
from vinylkit.tagging import tag_audio_file


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

    tag_audio_file(mock_mp3, sample_release, track_index=0)

    # Verify mutagen was used
    assert mock_mp3_class.called
    assert mock_audio.save.called


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
    from vinylkit.tagging import _calculate_track_and_disc

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
    t, d = _calculate_track_and_disc(
        release, 2, TrackNumbering.NUMERIC, DiscMapping.SINGLE
    )
    assert t == "3"
    assert d == "1"

    # 2. Per Side: Numeric resets, Discs 1, 2...
    t, d = _calculate_track_and_disc(
        release, 2, TrackNumbering.PER_SIDE, DiscMapping.PER_SIDE
    )
    assert t == "1"  # B1 is the 1st track on side B
    assert d == "2"  # Side B is disc 2

    # 3. Original: Keep A1
    t, d = _calculate_track_and_disc(
        release, 0, TrackNumbering.ORIGINAL, DiscMapping.SINGLE
    )
    assert t == "A1"
    assert d == "1"

    # 4. Physical: A,B=1, C,D=2
    # Test Side A
    t, d = _calculate_track_and_disc(
        release, 1, TrackNumbering.NUMERIC, DiscMapping.PHYSICAL
    )
    assert d == "1"  # A2 -> Disc 1
    # Test Side B
    t, d = _calculate_track_and_disc(
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
    t, d = _calculate_track_and_disc(
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
    t, d = _calculate_track_and_disc(
        release_prefix, 0, TrackNumbering.NUMERIC, DiscMapping.PHYSICAL
    )
    assert d == "1"
