"""Tests for utility functions: backup_file, sanitize_filename, ensure_absolute."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

from vinylkit.utils import backup_file, ensure_absolute, sanitize_filename


class TestBackupFile:
    def test_creates_backup_copy(self, tmp_path: Path) -> None:
        source = tmp_path / "song.mp3"
        source.write_text("audio data")
        backup_dir = tmp_path / "backups"

        result = backup_file(source, backup_dir)

        assert result.exists()
        assert result.read_text() == "audio data"
        assert result.parent == backup_dir

    def test_source_unchanged(self, tmp_path: Path) -> None:
        source = tmp_path / "song.mp3"
        source.write_text("original")
        backup_dir = tmp_path / "backups"

        backup_file(source, backup_dir)

        assert source.exists()
        assert source.read_text() == "original"

    def test_backup_naming_avoids_overwrite(self, tmp_path: Path) -> None:
        source = tmp_path / "song.mp3"
        source.write_text("v2")
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        # Pre-existing backup
        (backup_dir / "song.mp3").write_text("v1")

        result = backup_file(source, backup_dir)

        assert result.name == "song_backup.mp3"
        assert result.read_text() == "v2"
        assert (backup_dir / "song.mp3").read_text() == "v1"

    def test_creates_backup_dir_if_missing(self, tmp_path: Path) -> None:
        source = tmp_path / "song.mp3"
        source.write_text("data")
        backup_dir = tmp_path / "deep" / "nested" / "backups"

        result = backup_file(source, backup_dir)

        assert backup_dir.exists()
        assert result.exists()


class TestSanitizeFilename:
    def test_strips_illegal_characters(self) -> None:
        assert sanitize_filename('Back:In "Black"') == "Back_In _Black_"

    def test_handles_unicode(self) -> None:
        result = sanitize_filename("Caf\u00e9 Cr\u00e8me")
        assert "Caf\u00e9" in result

    def test_truncates_long_names(self) -> None:
        long_name = "A" * 300
        result = sanitize_filename(long_name)
        assert len(result.encode("utf-8")) <= 255

    def test_replaces_control_characters(self) -> None:
        result = sanitize_filename("bad\x00name\x1f")
        assert "\x00" not in result
        assert "\x1f" not in result


class TestEnsureAbsolute:
    def test_relative_becomes_absolute(self) -> None:
        result = ensure_absolute("relative/path")
        assert result.is_absolute()

    def test_absolute_unchanged(self, tmp_path: Path) -> None:
        result = ensure_absolute(tmp_path / "file.txt")
        assert result == tmp_path / "file.txt"

    def test_resolves_against_root(self, tmp_path: Path) -> None:
        result = ensure_absolute("subdir/file.txt", root=tmp_path)
        assert result.is_absolute()
        assert str(tmp_path) in str(result)
