from __future__ import annotations

from pathlib import Path

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

    assert "Discogs URI:   https://www.discogs.com/release/1978548" in content
    assert "Label:         Caravan Recordings (CVAN010)" in content
    assert 'Format:        2x Vinyl (12", Album)' in content
    assert "Mastered At: Wired Masters" in content
    assert "Design: John Coulthart" in content
    assert "Barcode: 5060096473954" in content


def test_save_artwork_multiple(tmp_path: Path):
    primary_data = b"primary cover"
    secondary_data = b"secondary art"

    # Save primary
    primary_path = save_artwork(tmp_path, primary_data, "folder.jpg", is_primary=True)
    assert primary_path.name == "folder.jpg"
    assert primary_path.read_bytes() == primary_data

    # Save secondary
    secondary_path = save_artwork(
        tmp_path, secondary_data, is_primary=False, subdir="Artwork"
    )
    assert secondary_path.parent.name == "Artwork"
    assert secondary_path.read_bytes() == secondary_data
    assert (tmp_path / "Artwork").exists()
    assert (tmp_path / "Artwork").is_dir()
