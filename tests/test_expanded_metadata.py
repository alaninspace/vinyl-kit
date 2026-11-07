from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import Any

from vinylkit.models import (
    CompanyInfo,
    DiscogsRelease,
    ExtraArtistInfo,
    FormatInfo,
    IdentifierInfo,
    LabelInfo,
    TrackInfo,
)
from vinylkit.tagging import save_artwork, write_release_info


def test_write_release_info_expanded(tmp_path: Path):
    release = DiscogsRelease(
        id=1978548,
        artists=["Emptyset"],
        title="Emptyset",
        tracklist=[TrackInfo("A1", "Aleph")],
        uri="https://www.discogs.com/release/1978548",
        labels=[LabelInfo("Caravan Recordings", "CVAN010")],
        companies=[CompanyInfo("Wired Masters", "Mastered At")],
        formats=[FormatInfo("Vinyl", "2", ['12"', "Album"])],
        identifiers=[IdentifierInfo("Barcode", "5060096473954")],
        extraartists=[ExtraArtistInfo("John Coulthart", "Design")],
        genres=["Electronic"],
        styles=["Techno"],
    )

    info_file = write_release_info(tmp_path, release, "info.txt")
    content = info_file.read_text(encoding="utf-8")

    assert "Discogs ID:    1978548" in content
    assert "Master URI:    N/A" in content
    assert "Release URI:   https://www.discogs.com/release/1978548" in content
    assert "Discogs URI:" not in content
    assert "CONTACT" not in content
    assert "Label:         Caravan Recordings (CVAN010)" in content
    assert 'Format:        2x Vinyl (12", Album)' in content
    assert "Mastered At: Wired Masters" in content
    assert "Design: John Coulthart" in content
    assert "Barcode: 5060096473954" in content


def _minimal_release(**kwargs: Any) -> DiscogsRelease:
    return DiscogsRelease(
        id=15204,
        artists=["Aron Akira", "Chab"],
        title="Jeux Sans Frontieres Volume 1",
        tracklist=[TrackInfo("A", "Slingshot")],
        uri="https://www.discogs.com/release/15204",
        **kwargs,
    )


def test_write_release_info_master_uri_above_release_uri(tmp_path: Path):
    release = _minimal_release(
        master_id=456961, master_url="https://www.discogs.com/master/456961"
    )
    lines = (
        write_release_info(tmp_path, release, "info.txt")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    idx = lines.index("Discogs ID:    15204")
    assert lines[idx + 1] == "Master URI:    https://www.discogs.com/master/456961"
    assert lines[idx + 2] == "Release URI:   https://www.discogs.com/release/15204"


def test_write_release_info_contact_after_notes(tmp_path: Path):
    release = _minimal_release(notes="Runouts are stamped.")
    content = write_release_info(
        tmp_path,
        release,
        "info.txt",
        contact_email="me@example.com",
        contact_website="example.com",
    ).read_text(encoding="utf-8")
    assert content.splitlines()[-8:] == [
        "NOTES",
        "-----",
        "Runouts are stamped.",
        "",
        "CONTACT",
        "-------",
        "  Email: me@example.com",
        "  Website: example.com",
    ]


def test_write_release_info_contact_without_notes_goes_last(tmp_path: Path):
    release = _minimal_release(identifiers=[IdentifierInfo("Barcode", "123")])
    content = write_release_info(
        tmp_path, release, "info.txt", contact_website="example.com"
    ).read_text(encoding="utf-8")
    assert "NOTES" not in content
    assert content.splitlines()[-5:] == [
        "  Barcode: 123",
        "",
        "CONTACT",
        "-------",
        "  Website: example.com",
    ]
    assert "Email:" not in content


def test_write_release_info_contact_email_only(tmp_path: Path):
    content = write_release_info(
        tmp_path, _minimal_release(), "info.txt", contact_email="me@example.com"
    ).read_text(encoding="utf-8")
    assert content.splitlines()[-3:] == [
        "CONTACT",
        "-------",
        "  Email: me@example.com",
    ]
    assert "Website:" not in content


def test_write_release_info_no_contact_when_unset(tmp_path: Path):
    content = write_release_info(
        tmp_path, _minimal_release(), "info.txt", contact_email=None
    ).read_text(encoding="utf-8")
    assert "CONTACT" not in content


def test_save_artwork_multiple(tmp_path: Path):
    primary_data = b"primary cover"
    secondary_data = b"secondary art"

    # Save primary
    primary_path = save_artwork(tmp_path, primary_data, "folder.jpg", is_primary=True)
    assert primary_path.name == "folder.jpg"
    assert primary_path.read_bytes() == primary_data

    # Save secondary
    secondary_path = save_artwork(
        tmp_path,
        secondary_data,
        filename="secondary_01.jpg",
        is_primary=False,
        subdir="Artwork",
    )
    assert secondary_path.parent.name == "Artwork"
    assert secondary_path.name == "secondary_01.jpg"
    assert secondary_path.read_bytes() == secondary_data
    assert (tmp_path / "Artwork").exists()
    assert (tmp_path / "Artwork").is_dir()
