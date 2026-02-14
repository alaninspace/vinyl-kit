"""Behavior-focused tests for replace/merge tagging modes.

Uses real audio files instead of mock-checking to verify actual tag behavior.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

from mutagen.mp3 import MP3

from vinylkit.models import DiscogsRelease, TagMode, TrackInfo
from vinylkit.tagging import tag_audio_file


def test_tag_mode_replace_clears_old_tags(mp3_file: Path) -> None:
    """Replace mode: only new tags should be present after tagging."""
    # Write initial tags
    first = DiscogsRelease(
        id=1,
        artists=["Old Artist"],
        title="Old Album",
        tracklist=[TrackInfo("A1", "Old Track")],
        genres=["Jazz"],
        styles=["Bebop"],
    )
    tag_audio_file(mp3_file, first, 0, tag_mode=TagMode.REPLACE)

    # Verify initial tags
    audio = MP3(mp3_file)
    assert str(audio.tags["TPE1"]) == "Old Artist"

    # Replace with new tags
    second = DiscogsRelease(
        id=2,
        artists=["New Artist"],
        title="New Album",
        tracklist=[TrackInfo("1", "New Track")],
        genres=["Rock"],
    )
    tag_audio_file(mp3_file, second, 0, tag_mode=TagMode.REPLACE)

    # Only new tags present
    audio = MP3(mp3_file)
    tags = audio.tags
    assert tags is not None
    assert str(tags["TPE1"]) == "New Artist"
    assert str(tags["TIT2"]) == "New Track"
    assert str(tags["TCON"]) == "Rock"
    # Old style tag should be gone (replace clears everything)
    assert not tags.getall("TXXX:STYLE")


def test_tag_mode_merge_preserves_old_tags(mp3_file: Path) -> None:
    """Merge mode: old tags should be preserved, new tags layered on top."""
    first = DiscogsRelease(
        id=1,
        artists=["Old Artist"],
        title="Old Album",
        tracklist=[TrackInfo("A1", "Old Track")],
        genres=["Jazz"],
    )
    tag_audio_file(mp3_file, first, 0, tag_mode=TagMode.REPLACE)

    # Merge new data on top
    second = DiscogsRelease(
        id=2,
        artists=["New Artist"],
        title="New Album",
        tracklist=[TrackInfo("1", "New Track")],
    )
    tag_audio_file(mp3_file, second, 0, tag_mode=TagMode.MERGE)

    audio = MP3(mp3_file)
    tags = audio.tags
    assert tags is not None
    # New values applied
    assert str(tags["TPE1"]) == "New Artist"
    assert str(tags["TIT2"]) == "New Track"
    # Old genre preserved (merge doesn't delete)
    assert str(tags["TCON"]) == "Jazz"
