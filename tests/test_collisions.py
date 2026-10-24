from __future__ import annotations

from conftest import create_mock_release

from vinylkit.cli import cli
from vinylkit.models import TrackInfo


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
        [
            "tag",
            str(source_dir),
            "--id",
            "123",
            "--rename",
            "--library-root",
            str(lib_dir),
        ],
        input="y\nn\n",
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
        [
            "tag",
            str(source_dir),
            "--id",
            "123",
            "--rename",
            "--library-root",
            str(lib_dir),
        ],
        input="y\ny\n",
    )

    assert "Warning: 1 destination file(s)/folder(s) already exist" in result.output
    assert "Files moved successfully" in result.output
    assert not (source_dir / "01.mp3").exists()
    assert dest_file.exists()
    assert dest_file.read_text() == "audio"


# ---------------------------------------------------------------------------
# Phase 1 in-place rename collision detection
# ---------------------------------------------------------------------------


def test_phase1_collision_aborts_with_error(runner, tmp_path, mock_discogs):
    """Phase 1 rename must detect when two files would collide."""
    source = tmp_path / "inbox"
    source.mkdir()
    (source / "01.mp3").write_text("a1")
    (source / "02.mp3").write_text("a2")

    lib_dir = tmp_path / "lib"

    # Create a release where two tracks produce the same filename
    # Use a naming pattern WITHOUT track_number so titles collide
    release = create_mock_release(
        123,
        "Artist",
        "Title",
        tracklist=[
            TrackInfo(position="A1", title="Same Name"),
            TrackInfo(position="A2", title="Same Name"),
        ],
    )
    mock_discogs.get_release.return_value = release

    config_path = tmp_path / "config.toml"
    config_path.write_text('naming_pattern = "{artist}/{album}/{title}"\n')

    result = runner.invoke(
        cli,
        [
            "tag",
            str(source),
            "--id",
            "123",
            "--rename",
            "--auto-move",
            "--library-root",
            str(lib_dir),
        ],
    )

    # Should report collision error, not silently overwrite
    assert "collide" in result.output.lower() or "failed" in result.output.lower()
    # Both source files should still exist (no data loss)
    assert (source / "01.mp3").exists()
    assert (source / "02.mp3").exists()


def test_phase1_collision_across_subfolders(runner, tmp_path, mock_discogs):
    """Same filename in different target subfolders must not clash in Phase 1."""
    source = tmp_path / "inbox"
    source.mkdir()
    (source / "01.mp3").write_text("side a")
    (source / "02.mp3").write_text("side b")

    release = create_mock_release(
        123,
        "Artist",
        "Title",
        tracklist=[
            TrackInfo(position="A1", title="Intro", side="A"),
            TrackInfo(position="B1", title="Intro", side="B"),
        ],
    )
    mock_discogs.get_release.return_value = release

    config_path = tmp_path / "config.toml"
    config_path.write_text('naming_pattern = "{artist}/{album}/{side}/{title}"\n')

    result = runner.invoke(
        cli,
        [
            "tag",
            str(source),
            "--id",
            "123",
            "--rename",
            "--auto-move",
            "--library-root",
            str(tmp_path / "lib"),
        ],
    )

    assert "collide" in result.output.lower()
    assert (source / "01.mp3").read_text() == "side a"
    assert (source / "02.mp3").read_text() == "side b"


def test_phase1_rename_does_not_overwrite_existing_file(runner, tmp_path, mock_discogs):
    """A new local name that matches another file in the folder must abort."""
    source = tmp_path / "inbox"
    source.mkdir()
    (source / "01.mp3").write_text("first")
    (source / "02.mp3").write_text("second")

    # Track 1 renames 01.mp3 -> 02.mp3, which still holds track 2's audio.
    release = create_mock_release(
        123,
        "Artist",
        "Title",
        tracklist=[
            TrackInfo(position="A1", title="02"),
            TrackInfo(position="A2", title="Other"),
        ],
    )
    mock_discogs.get_release.return_value = release

    config_path = tmp_path / "config.toml"
    config_path.write_text('naming_pattern = "{artist}/{album}/{title}"\n')

    result = runner.invoke(
        cli,
        ["tag", str(source), "--id", "123", "--rename", "--no-move"],
    )

    assert "would overwrite 02.mp3" in result.output
    assert (source / "01.mp3").read_text() == "first"
    assert (source / "02.mp3").read_text() == "second"


def test_batch_no_move_collision_abort(runner, tmp_path, mock_discogs):
    """--batch --no-move must prompt before overwriting files in the new folder."""
    parent = tmp_path / "inbox"
    album = parent / "Album [123]"
    album.mkdir(parents=True)
    (album / "01.mp3").write_text("new")

    existing = parent / "Artist" / "2000 - Title" / "A1 - Track 1.mp3"
    existing.parent.mkdir(parents=True)
    existing.write_text("existing")

    mock_discogs.get_release.return_value = create_mock_release(123, "Artist", "Title")

    result = runner.invoke(
        cli,
        ["tag", str(parent), "--batch", "--no-move"],
        input="n\n",
    )

    assert "Warning: 1 destination file(s)/folder(s) already exist" in result.output
    assert "Move aborted by user" in result.output
    assert existing.read_text() == "existing"
    assert (album / "A1 - Track 1.mp3").read_text() == "new"


def test_batch_no_move_collision_overwrite(runner, tmp_path, mock_discogs):
    """Confirming the prompt in --batch --no-move overwrites the target."""
    parent = tmp_path / "inbox"
    album = parent / "Album [123]"
    album.mkdir(parents=True)
    (album / "01.mp3").write_text("new")

    existing = parent / "Artist" / "2000 - Title" / "A1 - Track 1.mp3"
    existing.parent.mkdir(parents=True)
    existing.write_text("existing")

    mock_discogs.get_release.return_value = create_mock_release(123, "Artist", "Title")

    result = runner.invoke(
        cli,
        ["tag", str(parent), "--batch", "--no-move"],
        input="y\n",
    )

    assert "Files renamed into" in result.output
    assert existing.read_text() == "new"
    assert not album.exists()


def test_rename_commit_duplicate_targets(runner, tmp_path, mock_discogs):
    """rename --commit must refuse to move two tracks onto the same path."""
    source = tmp_path / "inbox"
    source.mkdir()
    (source / "01.mp3").write_text("a1")
    (source / "02.mp3").write_text("a2")

    release = create_mock_release(
        123,
        "Artist",
        "Title",
        tracklist=[
            TrackInfo(position="A1", title="Untitled"),
            TrackInfo(position="A2", title="Untitled"),
        ],
    )
    mock_discogs.get_release.return_value = release

    config_path = tmp_path / "config.toml"
    config_path.write_text('naming_pattern = "{artist}/{album}/{title}"\n')

    lib_dir = tmp_path / "lib"
    result = runner.invoke(
        cli,
        [
            "rename",
            str(source),
            "--id",
            "123",
            "--commit",
            "--library-root",
            str(lib_dir),
        ],
        input="y\n",
    )

    assert "collide" in result.output.lower()
    assert (source / "01.mp3").read_text() == "a1"
    assert (source / "02.mp3").read_text() == "a2"
    assert not lib_dir.exists()
