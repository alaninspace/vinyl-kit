from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from vinylkit.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_tag_no_id_fails(runner: CliRunner, tmp_path: Path) -> None:
    # Now it prompts for input if no ID/Search is provided
    result = runner.invoke(cli, ["tag", str(tmp_path)], input="\n")
    assert "Enter search query or Release ID" in result.output


def test_tag_invalid_path_fails(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["tag", "/non/existent/path", "--id", "123"])
    assert result.exit_code != 0
    assert "Directory '/non/existent/path' does not exist" in result.output
