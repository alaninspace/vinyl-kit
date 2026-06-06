from __future__ import annotations

from pathlib import Path

import pytest

from vinylkit.exceptions import FileOperationError
from vinylkit.models import DiscogsRelease, TrackInfo
from vinylkit.naming import generate_path, move_directory, move_file


def test_generate_path_basic() -> None:
    release = DiscogsRelease(
        id=1,
        artists=["AC/DC"],
        title="Back:In Black",
        year=1980,
        tracklist=[TrackInfo(position="A1", title="Hells Bells")],
    )
    pattern = "{artist}/{album}/{track_number} - {title}"
    root = Path("/music")

    new_path = generate_path(root, pattern, release, 0, ".mp3")

    # AC/DC should be sanitized, Back:In Black should be sanitized
    assert "AC_DC" in str(new_path)
    assert "Back_In Black" in str(new_path)
    assert "A1 - Hells Bells.mp3" in str(new_path)


def test_generate_path_custom_patterns() -> None:
    release = DiscogsRelease(
        id=12345,
        artists=["Pink Floyd"],
        title="Dark Side",
        year=1973,
        tracklist=[TrackInfo(position="A1", title="Speak to Me")],
        genres=["Rock"],
        country="UK",
    )
    root = Path("/music")

    # Flat structure
    pattern1 = "{id} - {artist} - {album} - {track_number}"
    path1 = generate_path(root, pattern1, release, 0, ".flac")
    assert "12345 - Pink Floyd - Dark Side - A1.flac" in str(path1)

    # Custom folder structure (Year - Album)
    pattern2 = "{year} - {album}/{title}"
    path2 = generate_path(root, pattern2, release, 0, ".flac")
    assert "1973 - Dark Side" in str(path2)
    assert "Speak to Me.flac" in str(path2)

    # Placeholder case sensitivity / new fields
    pattern3 = "{genre}/{country}/{discogs_id}/{title}"
    path3 = generate_path(root, pattern3, release, 0, ".mp3")
    assert "Rock/UK/12345/Speak to Me.mp3" in str(path3.as_posix())


def test_generate_path_strips_disambiguation() -> None:
    """Artists cleaned at parse time should produce clean folder names."""
    release = DiscogsRelease(
        id=92086,
        artists=["Pariah"],
        title="Test",
        year=1992,
        tracklist=[TrackInfo(position="A1", title="Track One")],
    )
    pattern = "{artist}/{year} - {album}/{track_number} - {title}"
    root = Path("/music")

    new_path = generate_path(root, pattern, release, 0, ".mp3")

    assert "Pariah" in str(new_path)
    assert "Pariah (2)" not in str(new_path)


def test_generate_path_dotted_vinyl_position() -> None:
    """Positions like B.1 / B.2 must not cause extension-stripping via with_suffix.

    Path("B.1 - Velociraptor").suffix returns ".1 - Velociraptor" (rightmost dot),
    so the old with_suffix(".flac") call would turn both B.1 and B.2 tracks into
    B.flac — causing a rename collision.
    """
    release = DiscogsRelease(
        id=236550,
        artists=["Agent 24K"],
        title="T. 1000",
        year=1993,
        tracklist=[
            TrackInfo(position="A", title="T. 1000", side="A"),
            TrackInfo(position="B.1", title="Velociraptor", side="B"),
            TrackInfo(position="B.2", title="Keep Moving", side="B"),
        ],
    )
    pattern = "{artist}/{year} - {album}/{track_number} - {title}"
    root = Path("/music")

    path_b1 = generate_path(root, pattern, release, 1, ".flac")
    path_b2 = generate_path(root, pattern, release, 2, ".flac")

    assert "B.1 - Velociraptor.flac" in str(path_b1)
    assert "B.2 - Keep Moving.flac" in str(path_b2)
    assert path_b1 != path_b2


def test_move_file_real(tmp_path: Path) -> None:
    from vinylkit.naming import move_file

    source = tmp_path / "source.mp3"
    source.write_text("audio content")
    target = tmp_path / "target.mp3"

    move_file(source, target, dry_run=False)

    assert not source.exists()
    assert target.exists()
    assert target.read_text() == "audio content"


def test_move_file_dry_run(tmp_path: Path) -> None:
    from vinylkit.naming import move_file

    source = tmp_path / "source.mp3"
    source.write_text("audio content")
    target = tmp_path / "target.mp3"

    move_file(source, target, dry_run=True)

    assert source.exists()
    assert not target.exists()


def test_move_file_creates_parent_dirs(tmp_path: Path) -> None:
    """move_file creates intermediate directories as needed."""
    from vinylkit.naming import move_file

    source = tmp_path / "source.flac"
    source.write_text("audio")
    target = tmp_path / "deep" / "nested" / "dir" / "track.flac"

    move_file(source, target, dry_run=False)

    assert not source.exists()
    assert target.read_text() == "audio"


def test_move_file_cross_root(tmp_path: Path) -> None:
    """move_file works when source and target are on different roots.

    We simulate a cross-root move by monkeypatching os.rename to raise
    the same error Windows raises for cross-drive moves, verifying that
    the shutil.move fallback (copy + delete) handles it.
    """
    from unittest.mock import patch

    from vinylkit.naming import move_file

    source = tmp_path / "src" / "track.flac"
    source.parent.mkdir()
    source.write_bytes(b"audio data")

    target = tmp_path / "dst" / "Artist" / "Album" / "track.flac"

    # Patch os.rename to raise the cross-device error that Windows gives
    def fake_rename(_src: str, _dst: str) -> None:
        raise OSError(17, "The system cannot move the file to a different disk drive")

    with patch("os.rename", side_effect=fake_rename):
        move_file(source, target, dry_run=False)

    assert not source.exists()
    assert target.exists()
    assert target.read_bytes() == b"audio data"


# ---------------------------------------------------------------------------
# move_directory safety
# ---------------------------------------------------------------------------


def test_move_directory_raises_when_target_exists(tmp_path: Path) -> None:
    source = tmp_path / "src_dir"
    source.mkdir()
    (source / "file.txt").write_text("data")

    target = tmp_path / "dst_dir"
    target.mkdir()
    (target / "existing.txt").write_text("precious")

    with pytest.raises(FileOperationError, match="already exists"):
        move_directory(source, target)

    # Original target data must survive
    assert (target / "existing.txt").read_text() == "precious"
    # Source must also survive (move never happened)
    assert (source / "file.txt").exists()


def test_move_directory_succeeds_when_target_absent(tmp_path: Path) -> None:
    source = tmp_path / "src_dir"
    source.mkdir()
    (source / "file.txt").write_text("data")

    target = tmp_path / "dst_dir"

    move_directory(source, target)

    assert (target / "file.txt").read_text() == "data"
    assert not source.exists()


def test_move_directory_dry_run(tmp_path: Path) -> None:
    source = tmp_path / "src_dir"
    source.mkdir()
    target = tmp_path / "dst_dir"

    move_directory(source, target, dry_run=True)

    assert source.exists()
    assert not target.exists()


# ---------------------------------------------------------------------------
# move_file exception handling
# ---------------------------------------------------------------------------


def test_move_file_missing_source_raises(tmp_path: Path) -> None:
    source = tmp_path / "nonexistent.mp3"
    target = tmp_path / "dest.mp3"

    with pytest.raises(FileOperationError, match="Failed to move"):
        move_file(source, target)


def test_generate_path_track_artist() -> None:
    from vinylkit.models import DiscogsRelease, TrackInfo
    from vinylkit.naming import generate_path

    release = DiscogsRelease(
        id=123,
        artists=["Various"],
        title="Album",
        tracklist=[
            TrackInfo(position="A1", title="Song", artists=["Track Artist"]),
        ],
    )

    pattern = "{artist}/{track_artist} - {title}"
    root = Path("/music")
    path = generate_path(root, pattern, release, 0, ".mp3")

    assert "Various/Track Artist - Song.mp3" in str(path.as_posix())


def test_generate_path_full_title() -> None:
    from vinylkit.models import DiscogsRelease, TrackInfo
    from vinylkit.naming import generate_path

    release = DiscogsRelease(
        id=123,
        artists=["Various"],
        title="Album",
        tracklist=[
            TrackInfo(position="A1", title="Song", artists=["Track Artist"]),
            TrackInfo(position="A2", title="Release Song"),
        ],
    )

    root = Path("/music")

    # Compilation track: should include artist
    path1 = generate_path(root, "{full_title}", release, 0, ".mp3")
    assert "Track Artist - Song.mp3" in str(path1.as_posix())

    # Release artist track: should NOT include artist (avoid redundancy)
    path2 = generate_path(root, "{full_title}", release, 1, ".mp3")
    assert path2.name == "Release Song.mp3"
