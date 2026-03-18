"""Tests for CLI commands that previously had zero coverage:
rename, scan, auth, config show/set.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

import pytest
from click.testing import CliRunner  # noqa: TC002
from conftest import create_mock_release

from vinylkit.cli import cli
from vinylkit.models import AppConfig

# ---------------------------------------------------------------------------
# rename command
# ---------------------------------------------------------------------------


class TestRenameCommand:
    def test_dry_run_by_default(
        self, runner: CliRunner, tmp_path: Path, mocker
    ) -> None:
        """Without --commit, rename shows planned moves but not execute."""
        folder = tmp_path / "album"
        folder.mkdir()
        (folder / "01.mp3").write_text("audio")

        mock_client = mocker.patch("vinylkit.commands._helpers.get_client").return_value
        mock_client.get_release.return_value = create_mock_release(
            123, "Artist", "Album"
        )
        spy_move = mocker.patch("vinylkit.commands._helpers.move_file")

        result = runner.invoke(cli, ["rename", str(folder), "--id", "123"])

        assert result.exit_code == 0
        assert "Dry-run" in result.output
        assert not spy_move.called

    def test_commit_moves_files(
        self, runner: CliRunner, tmp_path: Path, mocker
    ) -> None:
        """With --commit, files should actually be moved."""
        folder = tmp_path / "album"
        folder.mkdir()
        (folder / "01.mp3").write_text("audio")

        mock_client = mocker.patch("vinylkit.commands._helpers.get_client").return_value
        mock_client.get_release.return_value = create_mock_release(
            123, "Artist", "Album"
        )
        spy_move = mocker.patch("vinylkit.commands._helpers.move_file")
        mocker.patch("vinylkit.commands._helpers.move_directory")

        result = runner.invoke(
            cli,
            ["rename", str(folder), "--id", "123", "--commit"],
            input="y\n",
        )

        assert result.exit_code == 0
        assert spy_move.called

    def test_interactive_id_prompt(
        self, runner: CliRunner, tmp_path: Path, mocker
    ) -> None:
        """When --id is not provided, user should be prompted."""
        folder = tmp_path / "album"
        folder.mkdir()
        (folder / "01.mp3").write_text("audio")

        mock_client = mocker.patch("vinylkit.commands._helpers.get_client").return_value
        mock_client.get_release.return_value = create_mock_release(456, "Foo", "Bar")

        result = runner.invoke(cli, ["rename", str(folder)], input="456\n")

        assert result.exit_code == 0
        assert "Enter Discogs Release ID" in result.output


# ---------------------------------------------------------------------------
# scan command
# ---------------------------------------------------------------------------


class TestScanCommand:
    def test_scan_with_audio_files(self, runner: CliRunner, tmp_path: Path) -> None:
        (tmp_path / "a.mp3").write_text("data")
        (tmp_path / "b.flac").write_text("data")

        result = runner.invoke(cli, ["scan", str(tmp_path)])

        assert result.exit_code == 0
        assert "Scanning:" in result.output
        assert "Total files found:" in result.output

    def test_scan_no_audio_files(self, runner: CliRunner, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("hello")

        result = runner.invoke(cli, ["scan", str(tmp_path)])

        assert result.exit_code == 0
        assert "No supported audio files found" in result.output

    def test_scan_uses_recordings_root(
        self, runner: CliRunner, tmp_path: Path, mocker
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        (inbox / "track.mp3").write_text("data")
        mocker.patch(
            "vinylkit.cli.load_config",
            return_value=AppConfig(
                library_root=tmp_path / "lib", recordings_root=inbox
            ),
        )

        result = runner.invoke(cli, ["scan"])

        assert result.exit_code == 0
        assert "Scanning:" in result.output


# ---------------------------------------------------------------------------
# auth commands
# ---------------------------------------------------------------------------


class TestAuthCommands:
    def test_identity_success(self, runner: CliRunner, mocker) -> None:
        mock_client = mocker.patch("vinylkit.commands._helpers.get_client").return_value
        mock_client.get_identity.return_value = {
            "username": "testuser",
            "name": "Test User",
            "resource_url": "https://api.discogs.com/users/testuser",
        }

        result = runner.invoke(cli, ["auth", "identity"])

        assert result.exit_code == 0
        assert "testuser" in result.output

    def test_identity_not_authenticated(self, runner: CliRunner, mocker) -> None:
        from vinylkit.exceptions import DiscogsAPIError

        mock_client = mocker.patch("vinylkit.commands._helpers.get_client").return_value
        mock_client.get_identity.side_effect = DiscogsAPIError("Not authenticated")

        result = runner.invoke(cli, ["auth", "identity"])

        assert "Failed to get identity" in result.output

    def test_login_missing_consumer_key(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["auth", "login"])

        assert "consumer_key" in result.output


# ---------------------------------------------------------------------------
# config commands
# ---------------------------------------------------------------------------


class TestConfigCommands:
    def test_config_show_defaults(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["config", "show"])

        assert result.exit_code == 0
        assert "Config Path:" in result.output
        assert "library_root" in result.output
        assert "naming_pattern" in result.output
        # Verify section headers are present
        assert "General" in result.output
        assert "Metadata & Tagging" in result.output
        assert "Artwork" in result.output
        assert "Authentication" in result.output

    def test_config_set_string(self, runner: CliRunner) -> None:
        result = runner.invoke(
            cli,
            ["config", "set", "naming_pattern", "{artist}/{album}/{title}"],
        )
        assert result.exit_code == 0
        assert "Successfully set" in result.output

        # Verify it persists
        show = runner.invoke(cli, ["config", "show"])
        assert "{artist}/{album}/{title}" in show.output

    def test_config_set_bool(self, runner: CliRunner) -> None:
        runner.invoke(cli, ["config", "set", "auto_move", "true"])
        show = runner.invoke(cli, ["config", "show"])
        assert "True" in show.output

    def test_config_set_int(self, runner: CliRunner) -> None:
        runner.invoke(cli, ["config", "set", "search_page_size", "20"])
        show = runner.invoke(cli, ["config", "show"])
        assert "20" in show.output

    def test_config_set_path(self, runner: CliRunner, tmp_path: Path) -> None:
        lib = str(tmp_path / "my_library")
        runner.invoke(cli, ["config", "set", "library_root", lib])
        show = runner.invoke(cli, ["config", "show"])
        # Strip table formatting — Rich wraps long paths across rows
        clean = show.output.replace("\u2502", "").replace("\n", "").replace(" ", "")
        assert "my_library" in clean

    def test_config_set_invalid_key(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["config", "set", "nonexistent_key", "val"])
        assert "Unknown configuration key" in result.output


# ---------------------------------------------------------------------------
# tag search loop quit uses click.exceptions.Exit
# ---------------------------------------------------------------------------


class TestTagQuitBehavior:
    def test_quit_exits_cleanly(self, runner, tmp_path, mock_discogs):
        """Quitting the tag search loop should use click.exceptions.Exit."""
        source = tmp_path / "inbox"
        source.mkdir()
        (source / "01.mp3").write_text("audio")

        mock_discogs.search_releases.return_value = [
            {
                "id": 1,
                "title": "Test",
                "year": "2020",
                "country": "US",
                "format": ["Vinyl"],
            }
        ]

        result = runner.invoke(
            cli,
            ["tag", str(source)],
            input="test query\nq\n",
        )

        assert result.exit_code == 0
        assert "Aborting tag session" in result.output


# ---------------------------------------------------------------------------
# batch tag
# ---------------------------------------------------------------------------


class TestBatchTag:
    @staticmethod
    def _suppress_moves(mocker):
        """Suppress file movement (mock_discogs doesn't patch these)."""
        mocker.patch("vinylkit.commands._helpers.move_file")
        mocker.patch("vinylkit.commands._helpers.move_directory")

    def test_batch_extracts_ids_from_bracket_folders(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        self._suppress_moves(mocker)
        parent = tmp_path / "inbox"
        parent.mkdir()
        f1 = parent / "Artist A [111]"
        f1.mkdir()
        (f1 / "01.mp3").write_text("a")
        f2 = parent / "Artist B [222]"
        f2.mkdir()
        (f2 / "01.mp3").write_text("a")

        r1 = create_mock_release(111, "A", "T")
        r2 = create_mock_release(222, "B", "T")
        mock_discogs.get_release.side_effect = [r1, r2]

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--batch", "--auto-move"],
        )
        assert result.exit_code == 0
        assert "2 succeeded" in result.output

    def test_batch_extracts_bare_numeric_folders(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        self._suppress_moves(mocker)
        parent = tmp_path / "inbox"
        parent.mkdir()
        f1 = parent / "99999"
        f1.mkdir()
        (f1 / "01.mp3").write_text("a")

        mock_discogs.get_release.return_value = create_mock_release(99999, "X", "Y")

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--batch", "--auto-move"],
        )
        assert result.exit_code == 0
        assert "1 succeeded" in result.output

    @pytest.mark.usefixtures("mock_discogs")
    def test_batch_skips_folders_without_id(self, runner, tmp_path, mocker) -> None:
        self._suppress_moves(mocker)
        parent = tmp_path / "inbox"
        parent.mkdir()
        f1 = parent / "No ID Here"
        f1.mkdir()
        (f1 / "01.mp3").write_text("a")

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--batch"],
        )
        assert result.exit_code == 0
        assert "1 skipped" in result.output
        assert "no Discogs ID" in result.output

    def test_batch_incompatible_with_id(self, runner, tmp_path) -> None:
        result = runner.invoke(
            cli,
            ["tag", str(tmp_path), "--batch", "--id", "123"],
        )
        assert result.exit_code != 0
        assert "--batch cannot be combined" in result.output

    def test_batch_incompatible_with_search(self, runner, tmp_path) -> None:
        result = runner.invoke(
            cli,
            ["tag", str(tmp_path), "--batch", "--search", "foo"],
        )
        assert result.exit_code != 0
        assert "--batch cannot be combined" in result.output

    def test_batch_incompatible_with_format(self, runner, tmp_path) -> None:
        result = runner.invoke(
            cli,
            ["tag", str(tmp_path), "--batch", "--format", "Vinyl"],
        )
        assert result.exit_code != 0
        assert "--batch cannot be combined" in result.output

    def test_batch_continues_after_failure(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        from vinylkit.exceptions import DiscogsAPIError

        self._suppress_moves(mocker)
        parent = tmp_path / "inbox"
        parent.mkdir()
        f1 = parent / "Album A [111]"
        f1.mkdir()
        (f1 / "01.mp3").write_text("a")
        f2 = parent / "Album B [222]"
        f2.mkdir()
        (f2 / "01.mp3").write_text("a")

        r2 = create_mock_release(222, "B", "T")
        mock_discogs.get_release.side_effect = [
            DiscogsAPIError("API error"),
            r2,
        ]

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--batch", "--auto-move"],
        )
        assert result.exit_code == 0
        assert "1 succeeded" in result.output
        assert "1 failed" in result.output

    def test_batch_continues_after_oserror(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        self._suppress_moves(mocker)
        parent = tmp_path / "inbox"
        parent.mkdir()
        f1 = parent / "Album A [111]"
        f1.mkdir()
        (f1 / "01.mp3").write_text("a")
        f2 = parent / "Album B [222]"
        f2.mkdir()
        (f2 / "01.mp3").write_text("a")

        r1 = create_mock_release(111, "A", "T")
        r2 = create_mock_release(222, "B", "T")
        mock_discogs.get_release.side_effect = [r1, r2]
        mocker.patch(
            "vinylkit.commands._helpers.tag_audio_file",
            side_effect=[PermissionError("denied"), mocker.DEFAULT],
        )

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--batch", "--auto-move"],
        )
        assert result.exit_code == 0
        assert "1 failed" in result.output
        assert "1 succeeded" in result.output

    def test_batch_respects_dry_run(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        self._suppress_moves(mocker)
        parent = tmp_path / "inbox"
        parent.mkdir()
        f1 = parent / "Album [555]"
        f1.mkdir()
        (f1 / "01.mp3").write_text("a")

        mock_discogs.get_release.return_value = create_mock_release(555, "A", "T")
        spy = mocker.patch(
            "vinylkit.commands._helpers.tag_audio_file",
        )

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--batch", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Dry-run complete" in result.output
        assert spy.call_args[1]["dry_run"] is True

    def test_batch_respects_no_rename(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        self._suppress_moves(mocker)
        parent = tmp_path / "inbox"
        parent.mkdir()
        f1 = parent / "Album [888]"
        f1.mkdir()
        (f1 / "01.mp3").write_text("a")

        mock_discogs.get_release.return_value = create_mock_release(888, "A", "T")
        spy_move = mocker.patch(
            "vinylkit.commands._helpers.move_file",
        )

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--batch", "--no-rename"],
        )
        assert result.exit_code == 0
        assert "1 succeeded" in result.output
        spy_move.assert_not_called()

    def test_batch_skips_track_count_mismatch(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        from vinylkit.models import TrackInfo

        self._suppress_moves(mocker)
        parent = tmp_path / "inbox"
        parent.mkdir()
        f1 = parent / "Album [777]"
        f1.mkdir()
        (f1 / "01.mp3").write_text("a")
        (f1 / "02.mp3").write_text("a")

        tracks = [TrackInfo(position=f"A{i}", title=f"T{i}") for i in range(1, 11)]
        mock_discogs.get_release.return_value = create_mock_release(
            777, "A", "T", tracklist=tracks
        )

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--batch", "--auto-move"],
        )
        assert result.exit_code == 0
        assert "1 skipped" in result.output
        assert "2 audio file(s)" in result.output
        assert "10 track(s)" in result.output

    def test_batch_no_move_renames_in_place(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        self._suppress_moves(mocker)
        parent = tmp_path / "inbox"
        parent.mkdir()
        f1 = parent / "Album [444]"
        f1.mkdir()
        (f1 / "01.mp3").write_text("a")

        mock_discogs.get_release.return_value = create_mock_release(444, "A", "T")

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--batch", "--no-move"],
        )
        assert result.exit_code == 0
        assert "1 succeeded" in result.output
        # Batch mode uses full naming pattern structure
        assert "renamed into" in result.output
        assert "A/2000 - T" in result.output

    def test_single_no_move_creates_subfolder(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        """Single-release --no-move creates a subfolder, not rename parent."""
        self._suppress_moves(mocker)
        folder = tmp_path / "my-rips"
        folder.mkdir()
        (folder / "01.mp3").write_text("a")

        mock_discogs.get_release.return_value = create_mock_release(165, "A", "T")

        result = runner.invoke(
            cli,
            ["tag", str(folder), "--id", "165", "--no-move"],
        )
        assert result.exit_code == 0
        # Should create full naming pattern structure inside path
        assert "organized into" in result.output
        assert "A/2000 - T" in result.output
        # Parent folder should NOT be renamed
        assert folder.exists()

    def test_no_move_incompatible_with_auto_move(self, runner, tmp_path) -> None:
        result = runner.invoke(
            cli,
            ["tag", str(tmp_path), "--no-move", "--auto-move"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


# ---------------------------------------------------------------------------
# tag --id subfolder resolution
# ---------------------------------------------------------------------------


class TestTagSubfolderResolution:
    """tag --id should descend into a matching subfolder when the parent has
    no audio files directly."""

    def test_id_descends_into_url_style_subfolder(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        """Files in '107536-Artist-Album/' are found when pointing at parent."""
        mocker.patch("vinylkit.commands._helpers.move_file")
        mocker.patch("vinylkit.commands._helpers.move_directory")
        parent = tmp_path / "Needledrop"
        parent.mkdir()
        subfolder = parent / "107536-Quivver-One-Last-Time"
        subfolder.mkdir()
        (subfolder / "01.mp3").write_text("a")

        mock_discogs.get_release.return_value = create_mock_release(
            107536, "Quivver", "One Last Time"
        )

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--id", "107536", "--no-move"],
        )
        assert result.exit_code == 0, result.output
        assert "Found release folder" in result.output
        assert "107536-Quivver-One-Last-Time" in result.output

    def test_id_uses_direct_folder_when_files_present(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        """When the specified folder already has audio files, it is used directly."""
        mocker.patch("vinylkit.commands._helpers.move_file")
        mocker.patch("vinylkit.commands._helpers.move_directory")
        folder = tmp_path / "my-rip"
        folder.mkdir()
        (folder / "01.mp3").write_text("a")

        mock_discogs.get_release.return_value = create_mock_release(999, "X", "Y")

        result = runner.invoke(
            cli,
            ["tag", str(folder), "--id", "999", "--no-move"],
        )
        assert result.exit_code == 0, result.output
        # No subfolder lookup message when files are directly present
        assert "Found release folder" not in result.output

    def test_id_warns_on_multiple_matching_subfolders(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        """When two subfolders share the same ID, a warning is emitted."""
        mocker.patch("vinylkit.commands._helpers.move_file")
        mocker.patch("vinylkit.commands._helpers.move_directory")
        parent = tmp_path / "inbox"
        parent.mkdir()
        sub1 = parent / "107536-Original-Press"
        sub1.mkdir()
        (sub1 / "01.mp3").write_text("a")
        sub2 = parent / "107536-Repress"
        sub2.mkdir()
        (sub2 / "01.mp3").write_text("a")

        mock_discogs.get_release.return_value = create_mock_release(
            107536, "Quivver", "One Last Time"
        )

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--id", "107536", "--no-move"],
        )
        assert result.exit_code == 0, result.output
        assert "multiple subfolders match ID" in result.output

    def test_id_oserror_is_caught_cleanly(
        self, runner, tmp_path, mock_discogs, mocker
    ) -> None:
        """An OSError during subfolder scan produces a clean error, not a traceback."""
        parent = tmp_path / "inbox"
        parent.mkdir()

        mocker.patch(
            "vinylkit.commands.tag._helpers.collect_audio_files",
            side_effect=OSError("permission denied"),
        )
        mock_discogs.get_release.return_value = create_mock_release(123, "X", "Y")

        result = runner.invoke(
            cli,
            ["tag", str(parent), "--id", "123"],
        )
        assert result.exit_code == 0
        assert "Tagging failed" in result.output
        assert "Traceback" not in result.output
