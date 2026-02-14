"""Config round-trip test: set values via CLI, read them back, verify."""

from __future__ import annotations

from click.testing import CliRunner  # noqa: TC002

from vinylkit.cli import cli


def test_config_round_trip(runner: CliRunner) -> None:
    """Verify config survives a full write -> read cycle across all value types."""
    settings = [
        ("naming_pattern", "{artist}/{album}/{title}"),
        ("auto_move", "true"),
        ("search_page_size", "15"),
        ("backup_enabled", "false"),
        ("artwork_subdir", "Art"),
        ("info_filename", "info.txt"),
    ]

    for key, value in settings:
        result = runner.invoke(cli, ["config", "set", key, value])
        assert result.exit_code == 0, f"Failed to set {key}: {result.output}"

    show = runner.invoke(cli, ["config", "show"])
    assert show.exit_code == 0

    assert "{artist}/{album}/{title}" in show.output
    assert "True" in show.output  # auto_move
    assert "15" in show.output  # search_page_size
    assert "Art" in show.output  # artwork_subdir
    assert "info.txt" in show.output
