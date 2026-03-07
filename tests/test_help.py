"""Tests for rich-click enhanced help output."""

from __future__ import annotations

import pytest

from vinylkit.cli import cli


def test_root_help_contains_description(runner) -> None:
    """Root help shows project description and Quick start."""
    result = runner.invoke(cli, ["-h"])
    assert result.exit_code == 0
    assert "VinylKit" in result.output
    assert "Quick start" in result.output


def test_h_alias_works_on_root(runner) -> None:
    """-h alias works the same as --help."""
    h_result = runner.invoke(cli, ["-h"])
    help_result = runner.invoke(cli, ["--help"])
    assert h_result.exit_code == 0
    assert help_result.exit_code == 0
    # Both should contain the same key content
    assert "Quick start" in h_result.output
    assert "Quick start" in help_result.output


@pytest.mark.parametrize(
    "cmd",
    [
        ["scan", "-h"],
        ["tag", "-h"],
        ["rename", "-h"],
        ["migrate", "-h"],
        ["auth", "-h"],
        ["config", "-h"],
        ["cache", "-h"],
        ["collection", "-h"],
    ],
)
def test_h_works_on_all_commands(runner, cmd: list[str]) -> None:
    """-h flag works on all commands and subgroups."""
    result = runner.invoke(cli, cmd)
    assert result.exit_code == 0


def test_root_help_shows_command_groups(runner) -> None:
    """Root help organises commands into groups."""
    result = runner.invoke(cli, ["-h"])
    assert "Core Commands" in result.output
    assert "Administration" in result.output


def test_config_set_help_lists_valid_keys(runner) -> None:
    """config set --help lists valid configuration keys."""
    result = runner.invoke(cli, ["config", "set", "-h"])
    assert result.exit_code == 0
    assert "library_root" in result.output
    assert "tag_mode" in result.output
    assert "skip_tags" in result.output


def test_tag_help_shows_examples(runner) -> None:
    """tag --help shows example commands."""
    result = runner.invoke(cli, ["tag", "-h"])
    assert result.exit_code == 0
    assert "vinylkit tag --id 19983" in result.output


def test_tag_help_shows_option_groups(runner) -> None:
    """tag --help shows option groups."""
    result = runner.invoke(cli, ["tag", "-h"])
    assert "Release Identification" in result.output
    assert "Output Control" in result.output


def test_migrate_help_shows_examples(runner) -> None:
    """migrate --help shows example commands."""
    result = runner.invoke(cli, ["migrate", "-h"])
    assert result.exit_code == 0
    assert "vinylkit migrate" in result.output


def test_rename_help_mentions_dry_run(runner) -> None:
    """rename --help mentions dry-run default."""
    result = runner.invoke(cli, ["rename", "-h"])
    assert result.exit_code == 0
    assert "dry-run" in result.output.lower()


def test_cache_clear_help_shows_examples(runner) -> None:
    """cache clear --help shows example commands."""
    result = runner.invoke(cli, ["cache", "clear", "-h"])
    assert result.exit_code == 0
    assert "vinylkit cache clear" in result.output
