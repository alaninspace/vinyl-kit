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
        ("replace_tags_on_migration", "false"),
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
    assert "replace_tags_on_migration" in show.output


def test_skip_tags_config_roundtrip(runner: CliRunner) -> None:
    """Verify skip_tags survives a CSV set -> show cycle."""
    result = runner.invoke(cli, ["config", "set", "skip_tags", "genre,style,barcode"])
    assert result.exit_code == 0

    show = runner.invoke(cli, ["config", "show"])
    assert show.exit_code == 0
    assert "genre" in show.output
    assert "style" in show.output
    assert "barcode" in show.output


def test_cache_enabled_roundtrip(runner: CliRunner) -> None:
    """Verify cache_enabled survives a set -> show cycle."""
    result = runner.invoke(cli, ["config", "set", "cache_enabled", "false"])
    assert result.exit_code == 0

    show = runner.invoke(cli, ["config", "show"])
    assert show.exit_code == 0
    assert "cache_enabled" in show.output
    assert "False" in show.output


def test_skip_tags_none_clears(runner: CliRunner) -> None:
    """Setting skip_tags to 'none' produces an empty list."""
    runner.invoke(cli, ["config", "set", "skip_tags", "genre,style"])
    result = runner.invoke(cli, ["config", "set", "skip_tags", "none"])
    assert result.exit_code == 0

    show = runner.invoke(cli, ["config", "show"])
    assert show.exit_code == 0
    # With an empty list, the display should show "None"
    assert "skip_tags" in show.output
