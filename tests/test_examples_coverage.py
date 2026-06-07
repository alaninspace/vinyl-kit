from __future__ import annotations

from pathlib import Path

import pytest
from conftest import create_mock_release

from vinylkit.cli import cli
from vinylkit.models import AppConfig, RateLimitInfo


@pytest.fixture
def mock_discogs(mocker):
    """Override shared mock_discogs to also suppress file movement."""
    mock_get_client = mocker.patch("vinylkit.commands._helpers.get_client")
    mock_client = mock_get_client.return_value
    mocker.patch("vinylkit.commands._helpers.tag_audio_file")
    mocker.patch("vinylkit.commands._helpers.clear_audio_tags")
    mocker.patch("vinylkit.commands._helpers.write_release_info")
    mocker.patch("vinylkit.commands._helpers.save_artwork")
    mocker.patch("vinylkit.commands._helpers.move_file")
    mocker.patch("vinylkit.commands._helpers.move_directory")
    mock_client.rate_limit_info = RateLimitInfo()
    return mock_client


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


def test_ex_1_3_id_rename_automove_delete_source(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag --id 53088 --rename --auto-move --delete-source"""
    src = tmp_path / "my-rips"
    src.mkdir()
    (src / "01.flac").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(
        53088, "The Prodigy", "Wind It Up"
    )
    result = runner.invoke(
        cli,
        [
            "tag",
            str(src),
            "--id",
            "53088",
            "--rename",
            "--auto-move",
            "--delete-source",
            "--library-root",
            str(tmp_path / "lib"),
        ],
    )
    # Verify the flag is accepted and command succeeds.
    # move_file is mocked in this file's fixture so actual deletion
    # is not tested here — see test_cli_commands.py for that.
    assert result.exit_code == 0


def test_ex_1_4_csv_ids_named_folders(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag --id 391682,30038 --library-root ... --rename --auto-move"""
    lib = tmp_path / "lib"
    for rid in (391682, 30038):
        folder = lib / str(rid)
        folder.mkdir(parents=True)
        (folder / "01.flac").write_text("audio")

    mock_discogs.get_release.side_effect = lambda rid: create_mock_release(
        rid, "Artist", f"Album {rid}"
    )
    result = runner.invoke(
        cli,
        [
            "tag",
            "--id",
            "391682,30038",
            "--library-root",
            str(lib),
            "--rename",
            "--auto-move",
        ],
    )
    assert result.exit_code == 0
    assert mock_discogs.get_release.call_count == 2


def test_ex_1_5_csv_ids_with_separate_source_folder(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag /unsorted --id 182338,74044 --library-root ...

    Flags: --rename --auto-move
    """
    unsorted = tmp_path / "unsorted"
    lib = tmp_path / "lib"
    lib.mkdir()
    for rid in (182338, 74044):
        folder = unsorted / str(rid)
        folder.mkdir(parents=True)
        (folder / "01.flac").write_text("audio")

    mock_discogs.get_release.side_effect = lambda rid: create_mock_release(
        rid, "Artist", f"Album {rid}"
    )
    result = runner.invoke(
        cli,
        [
            "tag",
            str(unsorted),
            "--id",
            "182338,74044",
            "--library-root",
            str(lib),
            "--rename",
            "--auto-move",
        ],
    )
    assert result.exit_code == 0
    assert mock_discogs.get_release.call_count == 2


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
    spy = mocker.patch("vinylkit.commands._helpers.tag_audio_file")
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


## 4b. Batch Mode Examples


def test_ex_batch_auto_move(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit tag --batch --auto-move"""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    mocker.patch(
        "vinylkit.cli.load_config",
        return_value=AppConfig(library_root=tmp_path / "lib", recordings_root=inbox),
    )
    f1 = inbox / "Artist [12345]"
    f1.mkdir()
    (f1 / "01.mp3").write_text("audio")

    mock_discogs.get_release.return_value = create_mock_release(
        12345, "Artist", "Album"
    )

    result = runner.invoke(cli, ["tag", "--batch", "--auto-move"])
    assert result.exit_code == 0
    assert "1 succeeded" in result.output


def test_ex_batch_explicit_path(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag /path/to/inbox --batch --auto-move"""
    parent = tmp_path / "inbox"
    parent.mkdir()
    f1 = parent / "Album [999]"
    f1.mkdir()
    (f1 / "01.mp3").write_text("audio")

    mock_discogs.get_release.return_value = create_mock_release(999, "A", "T")

    result = runner.invoke(
        cli,
        ["tag", str(parent), "--batch", "--auto-move"],
    )
    assert result.exit_code == 0
    assert "1 succeeded" in result.output


def test_ex_batch_url_style_folder_name(runner, tmp_path, mock_discogs, mocker):
    """Covers: batch mode with URL-style prefix folder name (e.g. 50224-Artist-Album)"""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    mocker.patch(
        "vinylkit.cli.load_config",
        return_value=AppConfig(library_root=tmp_path / "lib", recordings_root=inbox),
    )
    f1 = inbox / "50224-Breeder-New-York-FM-Rockstone"
    f1.mkdir()
    (f1 / "01.mp3").write_text("audio")

    mock_discogs.get_release.return_value = create_mock_release(
        50224, "Breeder", "New York FM"
    )

    result = runner.invoke(cli, ["tag", "--batch", "--auto-move"])
    assert result.exit_code == 0
    assert "1 succeeded" in result.output


def test_ex_batch_dry_run(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit tag --batch --dry-run"""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    mocker.patch(
        "vinylkit.cli.load_config",
        return_value=AppConfig(library_root=tmp_path / "lib", recordings_root=inbox),
    )
    f1 = inbox / "Album [555]"
    f1.mkdir()
    (f1 / "01.mp3").write_text("audio")

    mock_discogs.get_release.return_value = create_mock_release(555, "A", "T")
    spy = mocker.patch("vinylkit.commands._helpers.tag_audio_file")

    result = runner.invoke(cli, ["tag", "--batch", "--dry-run"])
    assert result.exit_code == 0
    assert "Dry-run complete" in result.output
    assert spy.call_args[1]["dry_run"] is True


def test_ex_batch_no_move(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit tag --batch --no-move"""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    mocker.patch(
        "vinylkit.cli.load_config",
        return_value=AppConfig(library_root=tmp_path / "lib", recordings_root=inbox),
    )
    f1 = inbox / "Album [333]"
    f1.mkdir()
    (f1 / "01.mp3").write_text("audio")

    mock_discogs.get_release.return_value = create_mock_release(333, "A", "T")

    result = runner.invoke(cli, ["tag", "--batch", "--no-move"])
    assert result.exit_code == 0
    assert "1 succeeded" in result.output
    assert "renamed into" in result.output


def test_ex_batch_interactive_windows(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag "D:\\Music\\DJ\\#Unsorted\\Vinyl"
    with flags: --batch --interactive --library-root
    --rename --auto-move --delete-source
    """
    unsorted = tmp_path / "Unsorted"
    unsorted.mkdir()
    f1 = unsorted / "Artist - Album"
    f1.mkdir()
    (f1 / "01.mp3").write_text("audio")

    mock_discogs.search_releases.return_value = [
        {"id": 999, "title": "Artist - Album", "year": "2020", "format": ["Vinyl"]}
    ]
    mock_discogs.get_release.return_value = create_mock_release(999, "Artist", "Album")

    result = runner.invoke(
        cli,
        [
            "tag",
            str(unsorted),
            "--batch",
            "--interactive",
            "--library-root",
            str(tmp_path / "Vinyl"),
            "--rename",
            "--auto-move",
            "--delete-source",
        ],
        input="1\ny\n",
    )
    assert result.exit_code == 0


def test_ex_batch_interactive_macos(runner, tmp_path, mock_discogs):
    """Covers: vinylkit tag "/Volumes/HomeMedia/Music/DJ/#Unsorted/Vinyl"
    with flags: --batch --interactive --library-root
    --rename --auto-move --delete-source
    """
    unsorted = tmp_path / "Unsorted"
    unsorted.mkdir()
    f1 = unsorted / "Artist - Album"
    f1.mkdir()
    (f1 / "01.mp3").write_text("audio")

    mock_discogs.search_releases.return_value = [
        {"id": 999, "title": "Artist - Album", "year": "2020", "format": ["Vinyl"]}
    ]
    mock_discogs.get_release.return_value = create_mock_release(999, "Artist", "Album")

    result = runner.invoke(
        cli,
        [
            "tag",
            str(unsorted),
            "--batch",
            "--interactive",
            "--library-root",
            str(tmp_path / "Vinyl"),
            "--rename",
            "--auto-move",
            "--delete-source",
        ],
        input="1\ny\n",
    )
    assert result.exit_code == 0


## 4c. Tag Flags: --no-artwork, --no-rename


def test_ex_4_5_no_artwork(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit tag --id 31 --no-artwork"""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(
        31, "Aphex Twin", "Selected Ambient Works 85-92"
    )
    spy = mocker.patch("vinylkit.commands._helpers.tag_audio_file")
    result = runner.invoke(cli, ["tag", str(tmp_path), "--id", "31", "--no-artwork"])
    assert result.exit_code == 0
    assert spy.call_args[1]["artwork_data"] is None


def test_ex_4_6_no_rename(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit tag --id 62122 --no-rename"""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "01.mp3").write_text("audio")
    mocker.patch(
        "vinylkit.cli.load_config",
        return_value=AppConfig(library_root=tmp_path / "lib", recordings_root=inbox),
    )
    mock_discogs.get_release.return_value = create_mock_release(
        62122, "Orbital", "Chime"
    )
    spy_move = mocker.patch("vinylkit.commands._helpers.move_file")
    result = runner.invoke(cli, ["tag", "--id", "62122", "--no-rename"])
    assert result.exit_code == 0
    spy_move.assert_not_called()


## 5. Rename & Organize


def test_ex_5_1_rename_dry_run(runner, tmp_path, mock_discogs):
    """Covers: vinylkit rename /path --id 6108"""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(
        6108, "Leftfield", "Leftism"
    )
    result = runner.invoke(cli, ["rename", str(tmp_path), "--id", "6108"])
    assert result.exit_code == 0
    assert "Dry-run" in result.output


def test_ex_5_2_rename_commit(runner, tmp_path, mock_discogs):
    """Covers: vinylkit rename /path --id 6108 --commit"""
    (tmp_path / "01.mp3").write_text("audio")
    mock_discogs.get_release.return_value = create_mock_release(
        6108, "Leftfield", "Leftism"
    )
    result = runner.invoke(
        cli,
        ["rename", str(tmp_path), "--id", "6108", "--commit"],
        input="y\n",
    )
    assert result.exit_code == 0


## 6. Configuration Examples


def test_ex_5_1_config_auto_move(runner):
    """Covers: vinylkit config set auto_move true"""
    with runner.isolated_filesystem():
        runner.invoke(cli, ["config", "set", "auto_move", "true"])
        result = runner.invoke(cli, ["config", "show"])
        assert "auto_move" in result.output
        assert "True" in result.output


def test_ex_5_2_config_page_size(runner):
    """Covers: vinylkit config set search_page_size 10"""
    with runner.isolated_filesystem():
        runner.invoke(cli, ["config", "set", "search_page_size", "10"])
        result = runner.invoke(cli, ["config", "show"])
        assert "search_page_size" in result.output
        assert "10" in result.output


def test_ex_5_3_config_naming_pattern(runner):
    """Covers: vinylkit config set naming_pattern ..."""
    pattern = "{artist}/{label}/[{year}] {album}/{track_number} - {title}"
    with runner.isolated_filesystem():
        runner.invoke(cli, ["config", "set", "naming_pattern", pattern])
        result = runner.invoke(cli, ["config", "show"])
        assert "naming_pattern" in result.output
        # Strip table formatting — Rich wraps long values across rows
        clean = result.output.replace("\u2502", "").replace("\n", "").replace(" ", "")
        assert pattern.replace(" ", "") in clean


def test_ex_6_6_config_normalize_duplicates(runner):
    """Covers: vinylkit config set normalize_discogs_duplicates true/false"""
    with runner.isolated_filesystem():
        runner.invoke(cli, ["config", "set", "normalize_discogs_duplicates", "false"])
        result_off = runner.invoke(cli, ["config", "show"])
        assert "normalize_discogs_duplicates" in result_off.output
        assert "False" in result_off.output

        runner.invoke(cli, ["config", "set", "normalize_discogs_duplicates", "true"])
        result_on = runner.invoke(cli, ["config", "show"])
        assert "True" in result_on.output


def test_ex_6_4_config_show(runner):
    """Covers: vinylkit config show"""
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "library_root" in result.output
    assert "VinylKit" in result.output


def test_ex_6_5_version(runner):
    """Covers: vinylkit --version"""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output


## 7. Advanced Overrides


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
    spy = mocker.patch("vinylkit.commands._helpers.tag_audio_file")
    result = runner.invoke(cli, ["tag", str(tmp_path), "--id", "28203", "--merge"])
    assert result.exit_code == 0
    from vinylkit.models import TagMode

    assert spy.call_args[1]["tag_mode"] == TagMode.MERGE


## 8. Authentication


def test_ex_8_1_auth_identity(runner, mock_discogs):
    """Covers: vinylkit auth identity"""
    mock_discogs.get_identity.return_value = {
        "username": "testuser",
        "name": "Test User",
        "resource_url": "https://api.discogs.com/users/testuser",
    }
    result = runner.invoke(cli, ["auth", "identity"])
    assert result.exit_code == 0
    assert "testuser" in result.output


## 9. Collection Management


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


## 10. Library Migration


def test_ex_10_1_basic_migration(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit migrate ..."""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Jondi & Spesh [49135]"
    album_dir.mkdir()
    (album_dir / "track.mp3").write_text("audio")

    dest = tmp_path / "dest"
    mock_discogs.get_release.return_value = create_mock_release(49135, "J&S", "T")
    mocker.patch("vinylkit.commands._helpers.get_track_number", return_value="1")

    result = runner.invoke(cli, ["migrate", str(source), str(dest)], input="y\n")
    assert result.exit_code == 0
    assert "Migration complete!" in result.output


def test_ex_10_3_migration_filter_ids(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit migrate ... --id '49135,37623'"""
    source = tmp_path / "source"
    source.mkdir()
    a1 = source / "Album A [49135]"
    a1.mkdir()
    (a1 / "track.mp3").write_text("audio")
    a2 = source / "Album B [37623]"
    a2.mkdir()
    (a2 / "track.mp3").write_text("audio")
    a3 = source / "Album C [99999]"
    a3.mkdir()
    (a3 / "track.mp3").write_text("audio")

    dest = tmp_path / "dest"
    mock_discogs.get_release.side_effect = [
        create_mock_release(49135, "A", "T"),
        create_mock_release(37623, "B", "T"),
    ]
    mocker.patch("vinylkit.commands._helpers.get_track_number", return_value="1")

    result = runner.invoke(
        cli,
        ["migrate", str(source), str(dest), "--id", "49135,37623"],
        input="y\ny\n",
    )
    assert result.exit_code == 0
    assert "Skipping Album C" in result.output


def test_ex_10_4_migration_dry_run(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit migrate ... --dry-run"""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Peace Division [33511]"
    album_dir.mkdir()
    (album_dir / "track.mp3").write_text("audio")

    dest = tmp_path / "dest"
    mock_discogs.get_release.return_value = create_mock_release(33511, "PD", "T")
    mocker.patch("vinylkit.commands._helpers.get_track_number", return_value="1")

    result = runner.invoke(cli, ["migrate", str(source), str(dest), "--dry-run"])
    assert result.exit_code == 0
    assert "Dry-run" in result.output
    # Source should still exist since it's a dry-run
    assert album_dir.exists()


def test_ex_10_5_migration_replace_artwork_tags(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit migrate ... --replace-artwork --replace-tags"""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Test Album [12345]"
    album_dir.mkdir()
    (album_dir / "track.mp3").write_text("audio")

    dest = tmp_path / "dest"
    mock_discogs.get_release.return_value = create_mock_release(12345, "A", "T")
    mocker.patch("vinylkit.commands._helpers.get_track_number", return_value="1")

    result = runner.invoke(
        cli,
        [
            "migrate",
            str(source),
            str(dest),
            "--replace-artwork",
            "--replace-tags",
        ],
        input="y\n",
    )
    assert result.exit_code == 0
    assert "Migration complete!" in result.output


## 11. Cache Management


def test_ex_11_1_cache_list(runner, tmp_path, mocker):
    """Covers: vinylkit cache list"""
    import json

    mocker.patch("vinylkit.commands._helpers.get_cache_dir", return_value=tmp_path)
    data = {"id": 19983, "artists": [{"name": "Green Velvet"}], "title": "Flash"}
    (tmp_path / "release_19983.json").write_text(json.dumps(data))
    result = runner.invoke(cli, ["cache", "list"])
    assert result.exit_code == 0
    assert "19983" in result.output


def test_ex_11_2_cache_clear(runner, tmp_path, mocker):
    """Covers: vinylkit cache clear --yes"""
    import json

    mocker.patch("vinylkit.commands._helpers.get_cache_dir", return_value=tmp_path)
    data = {"id": 19983, "artists": [{"name": "Green Velvet"}], "title": "Flash"}
    (tmp_path / "release_19983.json").write_text(json.dumps(data))
    result = runner.invoke(cli, ["cache", "clear", "--yes"])
    assert result.exit_code == 0
    assert "Cleared 1" in result.output


def test_ex_11_3_cache_clear_single(runner, tmp_path, mocker):
    """Covers: vinylkit cache clear --id 19983"""
    import json

    mocker.patch("vinylkit.commands._helpers.get_cache_dir", return_value=tmp_path)
    data = {"id": 19983, "artists": [{"name": "Green Velvet"}], "title": "Flash"}
    (tmp_path / "release_19983.json").write_text(json.dumps(data))
    result = runner.invoke(cli, ["cache", "clear", "--id", "19983"])
    assert result.exit_code == 0
    assert "Cleared cache for release 19983" in result.output


def test_ex_11_4_cache_clear_interactive(runner, tmp_path, mocker):
    """Covers: vinylkit cache clear (interactive confirmation)"""
    import json

    mocker.patch("vinylkit.commands._helpers.get_cache_dir", return_value=tmp_path)
    data = {"id": 19983, "artists": [{"name": "Green Velvet"}], "title": "Flash"}
    (tmp_path / "release_19983.json").write_text(json.dumps(data))
    result = runner.invoke(cli, ["cache", "clear"], input="y\n")
    assert result.exit_code == 0
    assert "Cleared 1" in result.output


def test_ex_11_5_cache_clear_short_flag(runner, tmp_path, mocker):
    """Covers: vinylkit cache clear -y"""
    import json

    mocker.patch("vinylkit.commands._helpers.get_cache_dir", return_value=tmp_path)
    data = {"id": 53088, "artists": [{"name": "The Prodigy"}], "title": "Wind It Up"}
    (tmp_path / "release_53088.json").write_text(json.dumps(data))
    result = runner.invoke(cli, ["cache", "clear", "-y"])
    assert result.exit_code == 0
    assert "Cleared 1" in result.output


def test_ex_11_6_config_cache_disabled(runner):
    """Covers: vinylkit config set cache_enabled false"""
    result = runner.invoke(cli, ["config", "set", "cache_enabled", "false"])
    assert result.exit_code == 0
    show = runner.invoke(cli, ["config", "show"])
    assert show.exit_code == 0
    assert "False" in show.output


def test_ex_10_2_migration_with_delete(runner, tmp_path, mock_discogs, mocker):
    """Covers: vinylkit migrate ... --delete"""
    source = tmp_path / "source"
    source.mkdir()
    album_dir = source / "Peace Division [33511]"
    album_dir.mkdir()
    (album_dir / "track.mp3").write_text("audio")

    dest = tmp_path / "dest"
    mock_discogs.get_release.return_value = create_mock_release(33511, "PD", "T")
    mocker.patch("vinylkit.commands._helpers.get_track_number", return_value="1")

    result = runner.invoke(
        cli, ["migrate", str(source), str(dest), "--delete"], input="y\n"
    )
    assert result.exit_code == 0
    assert not album_dir.exists()


## 12. Getting Help Examples


def test_ex_12_1_root_help(runner) -> None:
    """Covers: vinylkit -h"""
    result = runner.invoke(cli, ["-h"])
    assert result.exit_code == 0
    assert "VinylKit" in result.output


def test_ex_12_2_tag_help(runner) -> None:
    """Covers: vinylkit tag -h"""
    result = runner.invoke(cli, ["tag", "-h"])
    assert result.exit_code == 0
    assert "Release Identification" in result.output


def test_ex_12_3_config_set_help(runner) -> None:
    """Covers: vinylkit config set -h"""
    result = runner.invoke(cli, ["config", "set", "-h"])
    assert result.exit_code == 0
    assert "library_root" in result.output
