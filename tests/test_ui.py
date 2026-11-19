"""Tests for the shared output helpers and the layout rules they enforce.

The rule under test: no line is padded out to a right-hand border, so
output re-wraps as plain text when a terminal is resized after printing.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import pytest
from rich.console import Console
from rich.text import Text

from vinylkit import ui
from vinylkit.cli import cli

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner

BORDER_CHARS = "│┃┌┐└┘├┤┬┴┼╭╮╰╯"
WIDTHS = [40, 60, 80, 100, 160]


def assert_reflow_safe(output: str) -> None:
    """Fail if *output* has borders or padding that break on a resize."""
    for line in output.splitlines():
        assert line == line.rstrip(), f"trailing whitespace: {line!r}"
        assert not set(line) & set(BORDER_CHARS), f"border character: {line!r}"


@pytest.fixture
def capture(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    """Point the shared console at a buffer and return the buffer."""
    buffer = io.StringIO()
    # Patch the private slot: the public ``file`` property falls back to
    # the live sys.stdout, and restoring a captured stdout would pin it.
    monkeypatch.setattr(ui.console, "_file", buffer)
    return buffer


class TestMessages:
    def test_success_warning_error_prefixes(self, capture: io.StringIO) -> None:
        ui.success("Tagged 4 tracks")
        ui.warning("Cache is empty.")
        ui.error("Release not found.", "Check the ID.")
        assert capture.getvalue().splitlines() == [
            "✓ Tagged 4 tracks",
            "! Cache is empty.",
            "✗ Release not found.",
            "  Check the ID.",
        ]

    def test_ascii_fallback_on_non_utf8_output(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252")
        monkeypatch.setattr(ui, "console", Console(file=stream))
        ui.success("Done")
        ui.error("Failed")
        stream.flush()
        assert raw.getvalue().decode("cp1252").splitlines() == [
            "ok: Done",
            "error: Failed",
        ]

    def test_long_message_is_not_hard_wrapped(
        self, capture: io.StringIO, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COLUMNS", "40")
        message = "word " * 30
        ui.warning(message.strip())
        assert len(capture.getvalue().splitlines()) == 1

    def test_heading_with_detail(self, capture: io.StringIO) -> None:
        ui.heading("19983", "in /music/inbox")
        assert capture.getvalue() == "19983  in /music/inbox\n"


class TestTable:
    @pytest.mark.parametrize("width", WIDTHS)
    def test_rows_fit_and_have_no_padding(
        self, width: int, capture: io.StringIO, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COLUMNS", str(width))
        table = ui.make_table()
        table.add_column("ID", no_wrap=True)
        table.add_column("Title", overflow="fold")
        table.add_row("1", "short")
        table.add_row("2", "a much longer title " * 12)
        ui.print_table(table)
        output = capture.getvalue()
        assert_reflow_safe(output)
        limit = min(width, ui.MAX_WIDTH)
        assert max(len(line) for line in output.splitlines()) <= limit

    def test_short_table_stays_narrow_in_a_wide_terminal(
        self, capture: io.StringIO, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COLUMNS", "200")
        table = ui.make_table()
        table.add_column("Side")
        table.add_row("A")
        ui.print_table(table)
        assert max(len(line) for line in capture.getvalue().splitlines()) < 10


class TestSection:
    ROWS = (
        ("library_root", Text("/music/vinyl")),
        ("naming_pattern", Text("{artist}/{year} - {album} [{label}]/{title}")),
    )

    @pytest.mark.parametrize("width", WIDTHS)
    def test_fits_width(
        self, width: int, capture: io.StringIO, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COLUMNS", str(width))
        ui.print_section("General", self.ROWS)
        output = capture.getvalue()
        assert_reflow_safe(output)
        assert max(len(line) for line in output.splitlines()) <= width

    def test_side_by_side_when_wide(
        self, capture: io.StringIO, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COLUMNS", "100")
        ui.print_section("General", self.ROWS)
        lines = capture.getvalue().splitlines()
        assert lines[0] == "General"
        assert lines[1].split() == ["library_root", "/music/vinyl"]
        # Brackets in values are literal text, not markup.
        assert "[{label}]" in lines[2]

    def test_values_stack_under_keys_when_narrow(
        self, capture: io.StringIO, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COLUMNS", str(ui.STACK_BELOW - 1))
        ui.print_section("General", self.ROWS)
        lines = capture.getvalue().splitlines()
        assert lines[1] == "  library_root"
        assert lines[2] == "    /music/vinyl"


class TestCommandLayout:
    """End-to-end: command output follows the layout rule at every width."""

    @pytest.mark.parametrize("width", WIDTHS)
    def test_config_show(
        self, width: int, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COLUMNS", str(width))
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        assert_reflow_safe(result.output)
        assert "normalize_discogs_duplicates" in result.output

    @pytest.mark.parametrize("width", WIDTHS)
    def test_help_has_no_borders(
        self, width: int, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COLUMNS", str(width))
        for args in (["-h"], ["tag", "-h"], ["config", "set", "-h"]):
            result = runner.invoke(cli, args)
            assert result.exit_code == 0
            assert not set(result.output) & set(BORDER_CHARS)

    @pytest.mark.parametrize(
        ("width", "country", "fmt"),
        [(60, False, False), (80, True, False), (100, True, True)],
    )
    def test_search_results_drop_columns_when_narrow(
        self,
        width: int,
        country: bool,
        fmt: bool,
        runner: CliRunner,
        tmp_path: Path,
        mock_discogs,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("COLUMNS", str(width))
        mock_discogs.search_releases.return_value = [
            {
                "id": 19983,
                "title": "Faithless - Insomnia",
                "catno": "CHEKXX 010",
                "year": 1995,
                "country": "UK",
                "format": ["Vinyl", '12"'],
            }
        ]
        result = runner.invoke(
            cli, ["tag", str(tmp_path), "--search", "insomnia"], input="q\n"
        )
        assert result.exit_code == 0
        assert_reflow_safe(result.output.split("Select a release")[0])
        assert "19983" in result.output
        assert "Faithless - Insomnia" in result.output
        # The release URL is a hyperlink on the ID, not a column.
        assert "discogs.com/release" not in result.output
        assert ("Country" in result.output) is country
        assert ("Format" in result.output) is fmt

    def test_scan_table(
        self,
        runner: CliRunner,
        mp3_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("COLUMNS", "60")
        result = runner.invoke(cli, ["scan", str(mp3_file.parent)])
        assert result.exit_code == 0
        assert "Status" in result.output
        assert_reflow_safe(result.output)
