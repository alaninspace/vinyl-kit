from __future__ import annotations

from pathlib import Path
from vinylkit.models import DiscogsRelease, TrackInfo
from vinylkit.naming import generate_path


def test_generate_path_basic() -> None:
    release = DiscogsRelease(
        id=1, artists=["AC/DC"], title="Back:In Black", year=1980,
        tracklist=[TrackInfo(position="A1", title="Hells Bells")]
    )
    pattern = "{artist}/{album}/{track_number} - {title}"
    root = Path("/music")
    
    new_path = generate_path(root, pattern, release, 0, ".mp3")
    
    # AC/DC should be sanitized, Back:In Black should be sanitized
    assert "AC_DC" in str(new_path)
    assert "Back_In Black" in str(new_path)
    assert "A1 - Hells Bells.mp3" in str(new_path)


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
