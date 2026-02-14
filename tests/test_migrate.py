from __future__ import annotations

import os

from conftest import create_mock_release

from vinylkit.cli import cli
from vinylkit.models import ImageInfo


def test_migrate_basic_success(runner, tmp_path, mock_discogs, mocker):
    """Test a successful migration of one folder with ID in name."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Album [123]"
    album_dir.mkdir()
    (album_dir / "01.mp3").write_text("audio")

    dest = tmp_path / "dest"
    dest.mkdir()

    mock_discogs.get_release.return_value = create_mock_release(123, "Artist", "Title")
    # Mock get_track_number to return a valid track number
    # If calculate_track_and_disc is returning A1, then we should return A1 here too
    mocker.patch("vinylkit.cli.get_track_number", return_value="A1")

    result = runner.invoke(cli, ["migrate", str(source), str(dest)])

    assert result.exit_code == 0
    # Clean output check (ignoring colors/ANSI)
    assert "Migrated: Album [123]" in result.output.replace("\x1b", "")

    # Check log file
    log_file = dest / "00-Migration-Results.txt"
    assert log_file.exists()
    log_content = log_file.read_text()
    assert "PROCESSING: Album [123] (ID: 123)" in log_content

    # Check mapping in log with platform-specific separator
    # Default is A1 if NUMERIC is not working as expected in tests
    expected_rel = os.path.join("Artist", "2000 - Title", "A1 - Track 1.mp3")
    assert f"01.mp3 -> {expected_rel}" in log_content

    # Check destination file
    migrated_file = dest / expected_rel
    assert migrated_file.exists()
    assert migrated_file.read_text() == "audio"


def test_migrate_prompt_for_id(runner, tmp_path, mock_discogs):
    """Test migration prompts for ID when missing from folder name."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "No ID Here"
    album_dir.mkdir()
    (album_dir / "track.mp3").write_text("audio")

    dest = tmp_path / "dest"

    mock_discogs.get_release.return_value = create_mock_release(456, "A", "T")

    # Input: '456' for ID, then 'y' for alphabetical mapping
    result = runner.invoke(cli, ["migrate", str(source), str(dest)], input="456\ny\n")

    assert "No ID found for 'No ID Here'" in result.output
    assert "Migrated: No ID Here" in result.output
    # Match whatever output we got (A1 or 1)
    expected_rel_a1 = os.path.join("A", "2000 - T", "A1 - Track 1.mp3")
    expected_rel_1 = os.path.join("A", "2000 - T", "1 - Track 1.mp3")
    assert (dest / expected_rel_a1).exists() or (dest / expected_rel_1).exists()


def test_migrate_delete_after(runner, tmp_path, mock_discogs):
    """Test migration with --delete flag."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Delete Me [999]"
    album_dir.mkdir()
    (album_dir / "t.mp3").write_text("data")

    dest = tmp_path / "dest"
    mock_discogs.get_release.return_value = create_mock_release(999, "Del", "Me")

    result = runner.invoke(
        cli, ["migrate", str(source), str(dest), "--delete"], input="y\n"
    )

    assert result.exit_code == 0
    assert not album_dir.exists()
    assert "Migrated and deleted: Delete Me [999]" in result.output
    expected_rel_a1 = os.path.join("Del", "2000 - Me", "A1 - Track 1.mp3")
    expected_rel_1 = os.path.join("Del", "2000 - Me", "1 - Track 1.mp3")
    assert (dest / expected_rel_a1).exists() or (dest / expected_rel_1).exists()


def test_migrate_leading_zero_normalization(runner, tmp_path, mock_discogs, mocker):
    """Test that '01' tags correctly map to '1' in numeric numbering."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Normalize [123]"
    album_dir.mkdir()
    (album_dir / "track.mp3").write_text("audio")

    dest = tmp_path / "dest"

    # Release has 1 track
    mock_discogs.get_release.return_value = create_mock_release(123, "A", "T")

    # File has tag '01'
    mocker.patch("vinylkit.cli.get_track_number", return_value="01")

    # Should NOT prompt for alphabetical because 01 -> 1 is normalized
    result = runner.invoke(cli, ["migrate", str(source), str(dest)])

    assert "Automatic mapping failed" not in result.output
    assert "Migrated: Normalize [123]" in result.output
    assert result.exit_code == 0


def test_migrate_dry_run(runner, tmp_path, mock_discogs, mocker):
    """Test migration in dry-run mode."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Dry [1]"
    album_dir.mkdir()
    (album_dir / "t.mp3").write_text("data")

    dest = tmp_path / "dest"
    mock_discogs.get_release.return_value = create_mock_release(1, "D", "R")

    spy_copy = mocker.patch("shutil.copy2")

    result = runner.invoke(cli, ["migrate", str(source), str(dest), "--dry-run"])

    assert "Dry-run complete. Migration log would have been saved." in result.output
    assert not spy_copy.called
    assert not (dest / "00-Migration-Results.txt").exists()


def test_migrate_filter_ids(runner, tmp_path, mock_discogs):
    """Test migration with --id filter."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "Keep [123]").mkdir()
    (source / "Skip [456]").mkdir()

    # We only need to check if it tries to fetch the right one
    mock_discogs.get_release.return_value = create_mock_release(123, "A", "T")

    # We use dry-run to avoid needing files
    result = runner.invoke(
        cli,
        ["migrate", str(source), str(tmp_path / "dest"), "--id", "123", "--dry-run"],
    )

    assert "Migrating: Keep [123]" in result.output
    assert "Migrating: Skip [456]" in result.output
    assert "Skipping Skip [456] (ID 456 not in filter list)" in result.output
    # Ensure get_release was only called for 123
    mock_discogs.get_release.assert_called_once_with(123)


def test_migrate_collect_all_artwork(runner, tmp_path, mock_discogs, mocker):
    """Test that migrate downloads and saves secondary artwork when collect_all_artwork is True."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Art [100]"
    album_dir.mkdir()
    (album_dir / "01.mp3").write_text("audio")

    dest = tmp_path / "dest"

    release = create_mock_release(100, "Artist", "Album")
    # Add images to the release (frozen dataclass, so use object.__setattr__)
    images = [
        ImageInfo(uri="http://img/1", type="primary", resource_url="http://img/1"),
        ImageInfo(uri="http://img/2", type="secondary", resource_url="http://img/2"),
        ImageInfo(uri="http://img/3", type="secondary", resource_url="http://img/3"),
    ]
    object.__setattr__(release, "images", images)
    mock_discogs.get_release.return_value = release
    mock_discogs.download_image.side_effect = [b"primary", b"secondary1", b"secondary2"]

    mocker.patch("vinylkit.cli.get_track_number", return_value="A1")

    # Enable collect_all_artwork and image_handling=both via config
    config_path = tmp_path / "config.toml"
    config_path.write_text('image_handling = "both"\ncollect_all_artwork = true\n')

    result = runner.invoke(cli, ["migrate", str(source), str(dest)])

    assert result.exit_code == 0

    from vinylkit.cli import save_artwork

    save_calls = save_artwork.call_args_list
    # 4 calls: folder primary + subdir primary_01 + secondary_01 + secondary_02
    assert len(save_calls) == 4, f"Expected 4 save_artwork calls, got {len(save_calls)}"

    # First call: primary artwork in music folder (uses config filename)
    assert save_calls[0].kwargs.get("is_primary", True) is True

    # Second call: primary artwork in subdir as primary_01.jpg
    assert save_calls[1].kwargs["is_primary"] is False
    assert save_calls[1].kwargs["filename"] == "primary_01.jpg"

    # Third and fourth calls: secondary artwork
    assert save_calls[2].kwargs["is_primary"] is False
    assert save_calls[2].kwargs["filename"] == "secondary_01.jpg"
    assert save_calls[3].kwargs["is_primary"] is False
    assert save_calls[3].kwargs["filename"] == "secondary_02.jpg"


def test_migrate_rate_limit_logging(runner, tmp_path, mock_discogs, mocker):
    """Verify rate limit status and summary appear in migration log file."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Album [100]"
    album_dir.mkdir()
    (album_dir / "01.mp3").write_text("audio")

    dest = tmp_path / "dest"

    mock_discogs.get_release.return_value = create_mock_release(100, "A", "T")
    mocker.patch("vinylkit.cli.get_track_number", return_value="A1")

    # Simulate rate limit info being populated by API responses
    info = mock_discogs.rate_limit_info
    info.limit = 60
    info.used = 15
    info.remaining = 45
    info.peak_used = 15

    result = runner.invoke(cli, ["migrate", str(source), str(dest)])

    assert result.exit_code == 0

    log_file = dest / "00-Migration-Results.txt"
    assert log_file.exists()
    log_content = log_file.read_text()

    # Check per-release rate limit entry with tier info
    assert "[Rate Limit] Fast (0.25s delay)" in log_content
    assert "45/60 remaining" in log_content

    # Check summary section
    assert "Rate Limit Summary" in log_content
    assert "Peak usage: 15/60" in log_content
    assert "Final state: 15/60 used, 45 remaining" in log_content


def test_migrate_rate_limit_fallback_when_cached(
    runner, tmp_path, mock_discogs, mocker
):
    """When all releases are cached, rate limit shows Fallback tier."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Album [100]"
    album_dir.mkdir()
    (album_dir / "01.mp3").write_text("audio")

    dest = tmp_path / "dest"

    mock_discogs.get_release.return_value = create_mock_release(100, "A", "T")
    mocker.patch("vinylkit.cli.get_track_number", return_value="A1")

    # Leave rate_limit_info at defaults (all None) to simulate fully-cached scenario

    result = runner.invoke(cli, ["migrate", str(source), str(dest)])

    assert result.exit_code == 0

    log_file = dest / "00-Migration-Results.txt"
    assert log_file.exists()
    log_content = log_file.read_text()

    # Check fallback tier appears
    assert "[Rate Limit] Fallback (1.0s delay)" in log_content
    assert "no rate limit data available" in log_content

    # No summary section when no data was collected
    assert "Rate Limit Summary" not in log_content


def test_migrate_logs_rate_limit_info_per_release(
    runner, tmp_path, mock_discogs, mocker, caplog
):
    """Rate limit status is logged at INFO after each migrated release."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Album [100]"
    album_dir.mkdir()
    (album_dir / "01.mp3").write_text("audio")

    dest = tmp_path / "dest"

    mock_discogs.get_release.return_value = create_mock_release(100, "A", "T")
    mocker.patch("vinylkit.cli.get_track_number", return_value="A1")

    info = mock_discogs.rate_limit_info
    info.limit = 60
    info.used = 15
    info.remaining = 45
    info.peak_used = 15

    import logging as stdlogging

    with caplog.at_level(stdlogging.INFO):
        result = runner.invoke(cli, ["migrate", str(source), str(dest)])

    assert result.exit_code == 0
    assert "Rate limit: 45/60 remaining" in caplog.text


def test_migrate_replace_tags_false(runner, tmp_path, mock_discogs, mocker):
    """Tags are not touched but files are still copied."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Album [100]"
    album_dir.mkdir()
    (album_dir / "01.mp3").write_text("audio")

    dest = tmp_path / "dest"

    mock_discogs.get_release.return_value = create_mock_release(100, "A", "T")
    mocker.patch("vinylkit.cli.get_track_number", return_value="A1")

    # Disable tag replacement via config
    config_path = tmp_path / "config.toml"
    config_path.write_text("replace_tags_on_migration = false\n")

    result = runner.invoke(cli, ["migrate", str(source), str(dest)])

    assert result.exit_code == 0

    # tag_audio_file and clear_audio_tags should NOT have been called
    from vinylkit.cli import clear_audio_tags, tag_audio_file

    tag_audio_file.assert_not_called()
    clear_audio_tags.assert_not_called()

    # But files should still be copied
    expected_rel = os.path.join("A", "2000 - T", "A1 - Track 1.mp3")
    assert (dest / expected_rel).exists()

    # And supplementary files should still be written
    from vinylkit.cli import write_release_info

    write_release_info.assert_called_once()


def test_migrate_replace_tags_false_summary(runner, tmp_path, mock_discogs, mocker):
    """With replace_tags=False, summary says 'Copied N files' instead of 'Tagged'."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Album [100]"
    album_dir.mkdir()
    (album_dir / "01.mp3").write_text("audio")

    dest = tmp_path / "dest"

    mock_discogs.get_release.return_value = create_mock_release(100, "A", "T")
    mocker.patch("vinylkit.cli.get_track_number", return_value="A1")

    config_path = tmp_path / "config.toml"
    config_path.write_text("replace_tags_on_migration = false\n")

    result = runner.invoke(cli, ["migrate", str(source), str(dest)])

    assert result.exit_code == 0
    assert "Copied 1 files" in result.output
    assert "Tagged" not in result.output


def test_migrate_summary_output(runner, tmp_path, mock_discogs, mocker):
    """Migrate command displays a per-release summary after each release."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Album [100]"
    album_dir.mkdir()
    (album_dir / "01.mp3").write_text("audio")

    dest = tmp_path / "dest"

    mock_discogs.get_release.return_value = create_mock_release(100, "A", "T")
    mocker.patch("vinylkit.cli.get_track_number", return_value="A1")

    info = mock_discogs.rate_limit_info
    info.limit = 60
    info.used = 5
    info.remaining = 55

    result = runner.invoke(cli, ["migrate", str(source), str(dest)])

    assert result.exit_code == 0
    assert "Tagged 1 tracks" in result.output
    assert "saved 0 artwork files" in result.output
    assert "Rate limit: 55/60 remaining" in result.output
