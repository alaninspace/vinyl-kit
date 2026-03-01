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
