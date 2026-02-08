from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from vinylkit.cli import cli
from vinylkit.models import AppConfig, DiscogsRelease, TrackInfo


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_discogs(mocker):
    """Setup a standard mock for Discogs interactions."""
    mock_get_client = mocker.patch("vinylkit.cli.get_client")
    mock_client = mock_get_client.return_value

    # Mock tagging and utility functions to avoid side effects
    mocker.patch("vinylkit.cli.tag_audio_file")
    mocker.patch("vinylkit.cli.write_release_info")
    mocker.patch("vinylkit.cli.move_file")
    mocker.patch("vinylkit.cli.move_directory")

    return mock_client


def create_mock_release(rid: int, artist: str, title: str) -> DiscogsRelease:
    return DiscogsRelease(
        id=rid,
        artists=[artist],
        title=title,
        year=2000,
        tracklist=[TrackInfo(position="A1", title="Track 1")],
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


## 1. Direct Tagging Examples


def test_ex_1_1_basic_id_tagging(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag --id 19983"""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(
        19983, "Green Velvet", "Flash"
    )
    result = runner.invoke(cli, ["tag", str(tmp_path), "--id", "19983"])
    assert result.exit_code == 0
    assert "Loaded Release: Green Velvet - Flash" in result.output


def test_ex_1_2_id_rename_automove(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag --id 53088 --rename --auto-move"""
    (tmp_path / "01.flac").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(
        53088, "The Prodigy", "Wind It Up"
    )
    result = runner.invoke(
        cli,
        [
            "tag",
            str(tmp_path),
            "--id",
            "53088",
            "--rename",
            "--auto-move",
            "--library-root",
            str(tmp_path / "lib"),
        ],
    )
    assert result.exit_code == 0
    assert "Files moved successfully" in result.output


## 2. Precision Searching Examples


def test_ex_2_1_filtered_search_artist_album(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag --artist 'Faithless' --album 'Insomnia'"""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.search_releases.return_value = [
        {
            "id": 61232,
            "title": "Faithless - Insomnia",
            "year": 1997,
            "country": "UK",
            "format": ["Vinyl"],
        }
    ]
    mock_discogs.get_release.return_value = create_mock_release(
        61232, "Faithless", "Insomnia"
    )
    result = runner.invoke(
        cli,
        ["tag", str(tmp_path), "--artist", "Faithless", "--album", "Insomnia"],
        input="1\ny\n",
    )
    assert result.exit_code == 0
    assert "Search Results for: Faithless" in result.output


def test_ex_2_2_filtered_search_multi_format(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag --artist 'The Chemical Brothers'
    --album 'Hey Boy Hey Girl' --format 'Vinyl, CD'"""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.search_releases.return_value = [
        {
            "id": 4008,
            "title": "Chemical Brothers - Hey Boy Hey Girl",
            "year": 1999,
            "country": "UK",
            "format": ["Vinyl"],
        }
    ]
    mock_discogs.get_release.return_value = create_mock_release(
        4008, "The Chemical Brothers", "Hey Boy Hey Girl"
    )
    result = runner.invoke(
        cli,
        [
            "tag",
            str(tmp_path),
            "--artist",
            "The Chemical Brothers",
            "--album",
            "Hey Boy Hey Girl",
            "--format",
            "Vinyl, CD",
        ],
        input="1\ny\n",
    )
    assert result.exit_code == 0
    mock_discogs.search_releases.assert_called_with(
        None,
        artist="The Chemical Brothers",
        album="Hey Boy Hey Girl",
        format=["Vinyl", "CD"],
    )


## 3. Global Search Examples


def test_ex_3_1_global_search_catno(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag --search 'PLUS8028'"""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.search_releases.return_value = [
        {
            "id": 20754,
            "title": "Plastikman - Sheet One",
            "year": 1993,
            "country": "US",
            "format": ["Vinyl"],
        }
    ]
    mock_discogs.get_release.return_value = create_mock_release(
        20754, "Plastikman", "Sheet One"
    )
    result = runner.invoke(
        cli, ["tag", str(tmp_path), "--search", "PLUS8028"], input="1\ny\n"
    )
    assert result.exit_code == 0
    assert "Search Results for: PLUS8028" in result.output


def test_ex_3_2_global_search_artist_label(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag --search 'Jeff Mills Purpose Maker'"""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.search_releases.return_value = [
        {
            "id": 165,
            "title": "Jeff Mills - Kat Moda EP",
            "year": 1997,
            "country": "US",
            "format": ["Vinyl"],
        }
    ]
    mock_discogs.get_release.return_value = create_mock_release(
        165, "Jeff Mills", "Kat Moda EP"
    )
    result = runner.invoke(
        cli,
        ["tag", str(tmp_path), "--search", "Jeff Mills Purpose Maker"],
        input="1\ny\n",
    )
    assert result.exit_code == 0
    assert "Search Results for: Jeff Mills Purpose Maker" in result.output


## 4. Workflows & Scenarios


def test_ex_4_1_inbox_scan(runner, tmp_path, mocker):
    """Covers: vinylkit scan (with recordings_root set)"""
    inbox = tmp_path / "RecordedVinyl"
    inbox.mkdir()
    (inbox / "track.mp3").write_text("data")
    mocker.patch(
        "vinylkit.cli.load_config",
        return_value=AppConfig(library_root=tmp_path / "lib", recordings_root=inbox),
    )
    result = runner.invoke(cli, ["scan"])
    assert result.exit_code == 0
    assert "Scanning:" in result.output


def test_ex_4_2_inbox_tag(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit tag --artist 'Underworld' --album 'Born Slippy' (no path)"""
    inbox = tmp_path / "RecordedVinyl"
    inbox.mkdir()
    (inbox / "track.mp3").write_text("data")
    mocker.patch(
        "vinylkit.cli.load_config",
        return_value=AppConfig(library_root=tmp_path / "lib", recordings_root=inbox),
    )
    mock_discogs.search_releases.return_value = [
        {
            "id": 57745,
            "title": "Underworld - Born Slippy",
            "year": 1996,
            "country": "UK",
            "format": ["Vinyl"],
        }
    ]
    mock_discogs.get_release.return_value = create_mock_release(
        57745, "Underworld", "Born Slippy"
    )
    result = runner.invoke(
        cli, ["tag", "--artist", "Underworld", "--album", "Born Slippy"], input="1\ny\n"
    )
    assert result.exit_code == 0
    assert "Processing folder:" in result.output


def test_ex_4_3_dry_run(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit tag --id 1480380 --rename --dry-run"""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(
        1480380, "Massive Attack", "Unfinished Sympathy"
    )
    spy = mocker.patch("vinylkit.cli.tag_audio_file")
    result = runner.invoke(
        cli, ["tag", str(tmp_path), "--id", "1480380", "--rename", "--dry-run"]
    )
    assert result.exit_code == 0
    assert "Dry-run complete" in result.output
    assert spy.call_args[1]["dry_run"] is True


def test_ex_4_4_batch_processing(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag /path/* --rename"""
    f1 = tmp_path / "a1"
    f1.mkdir()
    f2 = tmp_path / "a2"
    f2.mkdir()
    (f1 / "t.mp3").write_text("a")
    (f2 / "t.mp3").write_text("a")
    mock_discogs.get_release.side_effect = [
        create_mock_release(1, "A", "T"),
        create_mock_release(2, "A", "T"),
    ]
    result = runner.invoke(
        cli, ["tag", str(f1), str(f2), "--rename"], input="1\ny\n2\ny\n"
    )
    assert result.exit_code == 0
    assert result.output.count("Processing folder:") == 2


## 5. Configuration Examples


def test_ex_5_1_config_auto_move(runner):
    """Covers: vinylkit config set auto_move true"""
    with runner.isolated_filesystem():
        runner.invoke(cli, ["config", "set", "auto_move", "true"])
        result = runner.invoke(cli, ["config", "show"])
        assert "Auto Move: True" in result.output


def test_ex_5_2_config_page_size(runner):
    """Covers: vinylkit config set search_page_size 10"""
    with runner.isolated_filesystem():
        runner.invoke(cli, ["config", "set", "search_page_size", "10"])
        result = runner.invoke(cli, ["config", "show"])
        assert "Search Page Size: 10" in result.output


def test_ex_5_3_config_naming_pattern(runner):
    """Covers: vinylkit config set naming_pattern ..."""
    pattern = "{artist}/{label}/[{year}] {album}/{track_number} - {title}"
    with runner.isolated_filesystem():
        runner.invoke(cli, ["config", "set", "naming_pattern", pattern])
        result = runner.invoke(cli, ["config", "show"])
        assert f"Naming Pattern: {pattern}" in result.output


## 6. Advanced Overrides


def test_ex_6_1_library_root_override(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag --id 236605 --rename --library-root ..."""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(
        236605, "Daft Punk", "Homework"
    )
    lib_over = tmp_path / "manual_lib"
    result = runner.invoke(
        cli,
        [
            "tag",
            str(tmp_path),
            "--id",
            "236605",
            "--rename",
            "--auto-move",
            "--library-root",
            str(lib_over),
        ],
    )
    assert result.exit_code == 0


def test_ex_6_2_merge_mode(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit tag --id 28203 --merge"""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(
        28203, "Satoshi Tomiie", "Love In Traffic"
    )
    spy = mocker.patch("vinylkit.cli.tag_audio_file")
    result = runner.invoke(cli, ["tag", str(tmp_path), "--id", "28203", "--merge"])
    assert result.exit_code == 0
    from vinylkit.models import TagMode

    assert spy.call_args[1]["tag_mode"] == TagMode.MERGE


## 7. Collection Management


def test_ex_7_1_collection_download(runner, mock_discogs):
    """Covers: vinylkit collection download"""
    # 1. Mock identity to get username
    mock_discogs.get_identity.return_value = {"username": "testuser"}

    # 2. Mock collection releases
    mock_discogs.get_collection_releases.return_value = [
        {
            "id": 123,
            "basic_information": {
                "artists": [{"name": "Green Velvet"}],
                "title": "Flash",
                "year": 1995,
                "labels": [{"name": "Relief", "catno": "RR001"}],
                "formats": [{"name": "Vinyl"}],
            },
        }
    ]

    # Run in isolated filesystem to check for the CSV file
    with runner.isolated_filesystem():
        import datetime

        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        expected_filename = f"{date_str}_testuser_collection.csv"

        # Test fresh download
        result = runner.invoke(cli, ["collection", "download"])
        assert result.exit_code == 0
        assert f"Collection saved to {expected_filename}" in result.output

        # Verify file exists
        csv_path = Path(expected_filename)
        assert csv_path.exists()

        # Test overwrite warning (Input 'y')
        result_ovr = runner.invoke(cli, ["collection", "download"], input="y\n")
        assert "already exists. Overwrite?" in result_ovr.output
        assert result_ovr.exit_code == 0

        # Test overwrite abort (Input 'n')
        result_abort = runner.invoke(cli, ["collection", "download"], input="n\n")
        assert "Download aborted" in result_abort.output
