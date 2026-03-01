"""Tests for CLI commands that previously had zero coverage:
rename, scan, auth, config show/set.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

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
