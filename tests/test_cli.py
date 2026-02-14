from __future__ import annotations

import logging as stdlogging
from pathlib import Path  # noqa: TC003

from click.testing import CliRunner
from conftest import create_mock_release

from vinylkit.cli import cli


def test_tag_no_id_fails(runner: CliRunner, tmp_path: Path) -> None:
    # Now it prompts for input if no ID/Search is provided
    result = runner.invoke(cli, ["tag", str(tmp_path)], input="\n")
    assert "Enter search query or Release ID" in result.output


def test_tag_invalid_path_fails(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["tag", "/non/existent/path", "--id", "123"])
    assert result.exit_code != 0
    assert "Directory '/non/existent/path' does not exist" in result.output


def test_tag_interactive_search_options(
    runner: CliRunner, tmp_path: Path, mocker
) -> None:
    # Mock the DiscogsClient so it doesn't make real requests
    mock_client = mocker.patch("vinylkit.cli.get_client")
    mock_inst = mock_client.return_value
    mock_inst.search_releases.return_value = [
        {
            "id": 123,
            "title": "Test Title",
            "year": 2000,
            "country": "US",
            "format": ["Vinyl"],
        }
    ]

    # Input '0' to skip after seeing the prompt
    result = runner.invoke(cli, ["tag", str(tmp_path)], input="test query\n0\n")

    # Verify the prompt contains our new options
    assert "Select a release (1-1)" in result.output
    assert "'r' to re-search" in result.output
    assert "'0' to skip" in result.output
    assert "'q' to quit" in result.output


def test_tag_auto_move_skips_confirm(runner: CliRunner, tmp_path: Path, mocker) -> None:
    # Setup mock files
    (tmp_path / "song.mp3").write_text("data")

    # Mock Discogs client and responses
    mock_get_client = mocker.patch("vinylkit.cli.get_client")
    mock_client = mock_get_client.return_value

    from vinylkit.models import DiscogsRelease, TrackInfo

    mock_release = DiscogsRelease(
        id=123,
        artists=["Artist"],
        title="Title",
        year=2000,
        tracklist=[TrackInfo(position="A1", title="Track")],
        labels=[],
        companies=[],
        formats=[],
        identifiers=[],
        extraartists=[],
        genres=[],
        styles=[],
        notes="",
        images=[],
        uri="",
    )
    mock_client.get_release.return_value = mock_release

    # Mock tagging and moving functions
    mocker.patch("vinylkit.cli.tag_audio_file")
    mocker.patch("vinylkit.cli.write_release_info")
    mock_move = mocker.patch("vinylkit.cli.move_file")

    # Mock click.confirm to ensure it's NOT called
    mock_confirm = mocker.patch("click.confirm", return_value=True)

    # Run tag with --auto-move and --id (to skip search)
    # We also need a library_root
    result = runner.invoke(
        cli,
        [
            "tag",
            str(tmp_path),
            "--id",
            "123",
            "--auto-move",
            "--library-root",
            str(tmp_path / "lib"),
            "--rename",
        ],
    )

    assert result.exit_code == 0
    assert "Files moved successfully" in result.output
    # confirm should NOT have been called because auto_move=True
    assert not mock_confirm.called
    assert mock_move.called


def test_tag_filtered_search_real_collection_example(
    runner: CliRunner, tmp_path: Path, mocker
) -> None:
    """Test a filtered search using a real release from the user's collection."""
    # Setup mock files
    (tmp_path / "track1.flac").write_text("audio")

    # Mock DiscogsClient
    mock_get_client = mocker.patch("vinylkit.cli.get_client")
    mock_client = mock_get_client.return_value

    # 1. Mock the search results (Faithless - Insomnia, ID 61232)
    mock_client.search_releases.return_value = [
        {
            "id": 61232,
            "title": "Faithless - Insomnia",
            "year": 1997,
            "country": "UK",
            "format": ["Vinyl", '12"', "Single"],
        }
    ]

    # 2. Mock the release fetch
    from vinylkit.models import DiscogsRelease, TrackInfo

    mock_release = DiscogsRelease(
        id=61232,
        artists=["Faithless"],
        title="Insomnia",
        year=1997,
        tracklist=[TrackInfo(position="A1", title="Insomnia (Monster Mix)")],
        labels=[],
        companies=[],
        formats=[],
        identifiers=[],
        extraartists=[],
        genres=["Electronic"],
        styles=["House"],
        notes="",
        images=[],
        uri="",
    )
    mock_client.get_release.return_value = mock_release

    # Mock operations
    mocker.patch("vinylkit.cli.tag_audio_file")
    mocker.patch("vinylkit.cli.write_release_info")
    mocker.patch("vinylkit.cli.move_file")

    # Run command with --artist and --album
    # Input "1" to select the first result
    result = runner.invoke(
        cli,
        [
            "tag",
            str(tmp_path),
            "--artist",
            "Faithless",
            "--album",
            "Insomnia",
            "--rename",
            "--auto-move",
        ],
        input="1\n",
    )

    assert result.exit_code == 0
    assert "Search Results for: Faithless" in result.output
    assert "Loaded Release: Faithless - Insomnia" in result.output
    assert "Files moved successfully" in result.output


def test_tag_logs_rate_limit_info_per_release(runner, tmp_path, mock_discogs, caplog):
    """Rate limit status is logged at INFO after each tagged release."""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(100, "Artist", "Title")

    info = mock_discogs.rate_limit_info
    info.limit = 60
    info.used = 10
    info.remaining = 50

    with caplog.at_level(stdlogging.INFO):
        result = runner.invoke(cli, ["tag", str(tmp_path), "--id", "100"])

    assert result.exit_code == 0
    assert "Rate limit: 50/60 remaining" in caplog.text


def test_httpcore_debug_suppressed(tmp_path):
    """initialise_logging suppresses httpcore debug noise."""
    from vinylkit.cli import initialise_logging
    from vinylkit.models import AppConfig

    config = AppConfig(library_root=tmp_path, log_to_file=False)
    initialise_logging(config)

    assert stdlogging.getLogger("httpcore").level == stdlogging.WARNING
    assert stdlogging.getLogger("httpx").level == stdlogging.WARNING


def test_tag_summary_output(runner, tmp_path, mock_discogs):
    """Tag command displays a counted summary after tagging."""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(100, "Artist", "Title")

    result = runner.invoke(cli, ["tag", str(tmp_path), "--id", "100"])

    assert result.exit_code == 0
    assert "Tagged 1 tracks" in result.output
    assert "saved 0 artwork files" in result.output


def test_tag_passes_skip_tags(runner, tmp_path, mock_discogs, mocker):
    """skip_tags from config is forwarded as frozenset to tag_audio_file."""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(100, "Artist", "Title")

    # Patch tag_audio_file to capture kwargs
    mock_tag = mocker.patch("vinylkit.cli.tag_audio_file")

    # Set skip_tags via config file
    from vinylkit.config import get_config_path, save_config
    from vinylkit.models import AppConfig

    cfg = AppConfig(library_root=tmp_path, skip_tags=["genre", "style"])
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    save_config(cfg)

    result = runner.invoke(cli, ["tag", str(tmp_path), "--id", "100"])
    assert result.exit_code == 0
    assert mock_tag.called
    call_kwargs = mock_tag.call_args
    assert call_kwargs.kwargs.get("skip_tags") == frozenset({"genre", "style"})


def test_release_separator_in_log(runner, tmp_path, mock_discogs, caplog):
    """Release separator line appears in logs at the start of processing."""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(100, "Artist", "Title")

    with caplog.at_level(stdlogging.INFO):
        result = runner.invoke(cli, ["tag", str(tmp_path), "--id", "100"])

    assert result.exit_code == 0
    assert "=== Release: Artist - Title (ID: 100) ===" in caplog.text
