from __future__ import annotations

from conftest import create_mock_release

from vinylkit.cli import cli


def test_tag_collision_abort(runner, tmp_path, mock_discogs):
    """Test that tagging aborts move if collision exists and user says 'n'."""
    # Setup source
    source_dir = tmp_path / "inbox"
    source_dir.mkdir()
    (source_dir / "01.mp3").write_text("audio")

    # Setup destination (collision)
    lib_dir = tmp_path / "lib"
    # Default pattern: {artist}/{year} - {album}/{track_number} - {title}
    # For our mock: Artist/2000 - Title/A1 - Track 1.mp3
    dest_file = lib_dir / "Artist" / "2000 - Title" / "A1 - Track 1.mp3"
    dest_file.parent.mkdir(parents=True)
    dest_file.write_text("existing")

    mock_discogs.get_release.return_value = create_mock_release(123, "Artist", "Title")

    # Run tag command with --rename
    # Input sequence:
    # 1. 'y' to "Proceed with moving files?"
    # 2. 'n' to "Overwrite existing files/folders?"
    result = runner.invoke(
        cli,
        ["tag", str(source_dir), "--id", "123", "--rename", "--library-root", str(lib_dir)],
        input="y\nn\n"
    )

    assert "Warning: 1 destination file(s)/folder(s) already exist" in result.output
    assert "Move aborted by user" in result.output
    assert dest_file.read_text() == "existing"

def test_tag_collision_overwrite(runner, tmp_path, mock_discogs):
    """Test that tagging overwrites if collision exists and user says 'y'."""
    source_dir = tmp_path / "inbox"
    source_dir.mkdir()
    (source_dir / "01.mp3").write_text("audio")

    lib_dir = tmp_path / "lib"
    dest_file = lib_dir / "Artist" / "2000 - Title" / "A1 - Track 1.mp3"
    dest_file.parent.mkdir(parents=True)
    dest_file.write_text("existing")

    mock_discogs.get_release.return_value = create_mock_release(123, "Artist", "Title")

    # Input 'y' twice
    result = runner.invoke(
        cli,
        ["tag", str(source_dir), "--id", "123", "--rename", "--library-root", str(lib_dir)],
        input="y\ny\n"
    )

    assert "Warning: 1 destination file(s)/folder(s) already exist" in result.output
    assert "Files moved successfully" in result.output
    assert not (source_dir / "01.mp3").exists()
    assert dest_file.exists()
    assert dest_file.read_text() == "audio"
