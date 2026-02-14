"""Tests for the cache list and cache clear CLI commands."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from click.testing import CliRunner  # noqa: TC002

if TYPE_CHECKING:
    from pathlib import Path

from vinylkit.cli import _format_age, cli


class TestFormatAge:
    """Unit tests for the _format_age helper."""

    def test_just_now(self) -> None:
        assert _format_age(time.time()) == "0m ago"

    def test_minutes(self) -> None:
        assert _format_age(time.time() - 30 * 60) == "30m ago"

    def test_hours(self) -> None:
        assert _format_age(time.time() - 3 * 3600) == "3h ago"

    def test_days(self) -> None:
        assert _format_age(time.time() - 5 * 86400) == "5d ago"

    def test_weeks(self) -> None:
        assert _format_age(time.time() - 21 * 86400) == "3w ago"

    def test_months(self) -> None:
        assert _format_age(time.time() - 90 * 86400) == "2mo ago"

    def test_years(self) -> None:
        assert _format_age(time.time() - 400 * 86400) == "1y ago"

    def test_future_timestamp(self) -> None:
        """Future timestamps should clamp to 0m ago."""
        assert _format_age(time.time() + 9999) == "0m ago"


def _write_cache_file(
    cache_dir: Path, release_id: int, artist: str, title: str
) -> Path:
    """Write a minimal cache JSON file."""
    data = {
        "id": release_id,
        "artists": [{"name": artist}],
        "title": title,
    }
    path = cache_dir / f"release_{release_id}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestCacheList:
    """Tests for the cache list subcommand."""

    def test_empty_cache(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=tmp_path)  # type: ignore[union-attr]
        result = runner.invoke(cli, ["cache", "list"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_missing_dir(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        missing = tmp_path / "nonexistent"
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=missing)  # type: ignore[union-attr]
        result = runner.invoke(cli, ["cache", "list"])
        assert result.exit_code == 0
        assert "does not exist" in result.output.lower()

    def test_lists_releases(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=tmp_path)  # type: ignore[union-attr]
        _write_cache_file(tmp_path, 12345, "Daft Punk", "Homework")
        result = runner.invoke(cli, ["cache", "list"])
        assert result.exit_code == 0
        assert "12345" in result.output
        assert "Daft Punk" in result.output
        assert "Homework" in result.output
        assert "1 cached release" in result.output

    def test_corrupt_file(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=tmp_path)  # type: ignore[union-attr]
        bad = tmp_path / "release_99999.json"
        bad.write_text("NOT JSON", encoding="utf-8")
        result = runner.invoke(cli, ["cache", "list"])
        assert result.exit_code == 0
        assert "corrupt" in result.output.lower()

    def test_multiple_releases(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=tmp_path)  # type: ignore[union-attr]
        _write_cache_file(tmp_path, 100, "A", "Album A")
        _write_cache_file(tmp_path, 200, "B", "Album B")
        _write_cache_file(tmp_path, 300, "C", "Album C")
        result = runner.invoke(cli, ["cache", "list"])
        assert result.exit_code == 0
        assert "3 cached release" in result.output


class TestCacheClear:
    """Tests for the cache clear subcommand."""

    def test_clear_all_with_yes(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=tmp_path)  # type: ignore[union-attr]
        _write_cache_file(tmp_path, 100, "A", "T")
        _write_cache_file(tmp_path, 200, "B", "T")
        result = runner.invoke(cli, ["cache", "clear", "--yes"])
        assert result.exit_code == 0
        assert "Cleared 2" in result.output
        assert not list(tmp_path.glob("release_*.json"))

    def test_clear_all_with_prompt(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=tmp_path)  # type: ignore[union-attr]
        _write_cache_file(tmp_path, 100, "A", "T")
        result = runner.invoke(cli, ["cache", "clear"], input="y\n")
        assert result.exit_code == 0
        assert "Cleared 1" in result.output

    def test_clear_all_abort(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=tmp_path)  # type: ignore[union-attr]
        _write_cache_file(tmp_path, 100, "A", "T")
        result = runner.invoke(cli, ["cache", "clear"], input="n\n")
        assert result.exit_code == 0
        assert "Aborted" in result.output
        assert list(tmp_path.glob("release_*.json"))

    def test_clear_single_found(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=tmp_path)  # type: ignore[union-attr]
        _write_cache_file(tmp_path, 100, "A", "T")
        _write_cache_file(tmp_path, 200, "B", "T")
        result = runner.invoke(cli, ["cache", "clear", "--id", "100"])
        assert result.exit_code == 0
        assert "Cleared cache for release 100" in result.output
        assert not (tmp_path / "release_100.json").exists()
        assert (tmp_path / "release_200.json").exists()

    def test_clear_single_not_found(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=tmp_path)  # type: ignore[union-attr]
        result = runner.invoke(cli, ["cache", "clear", "--id", "999"])
        assert result.exit_code == 0
        assert "No cache entry" in result.output

    def test_clear_empty_cache(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=tmp_path)  # type: ignore[union-attr]
        result = runner.invoke(cli, ["cache", "clear", "--yes"])
        assert result.exit_code == 0
        assert "already empty" in result.output.lower()

    def test_clear_missing_dir(
        self, runner: CliRunner, tmp_path: Path, mocker: object
    ) -> None:
        missing = tmp_path / "nonexistent"
        mocker.patch("vinylkit.cli.get_cache_dir", return_value=missing)  # type: ignore[union-attr]
        result = runner.invoke(cli, ["cache", "clear", "--yes"])
        assert result.exit_code == 0
        assert "does not exist" in result.output.lower()
