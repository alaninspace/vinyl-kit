from __future__ import annotations

from pathlib import Path

from vinylkit.models import DiscogsRelease, TrackInfo
from vinylkit.naming import generate_path


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
