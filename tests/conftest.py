from __future__ import annotations

import struct
from pathlib import Path  # noqa: TC003

import pytest
from click.testing import CliRunner

from vinylkit.models import DiscogsRelease, RateLimitInfo, TrackInfo


@pytest.fixture
def runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    """CLI runner with isolated config (prevents reading/writing real user config)."""
    config_path = tmp_path / "config.toml"
    monkeypatch.setenv("VINYLKIT_CONFIG", str(config_path))
    return CliRunner()


@pytest.fixture
def mock_discogs(mocker):
    """Shared mock for Discogs client and tagging side-effects.

    Does NOT mock move_file/move_directory — tests that need file
    movement suppressed should patch those themselves.
    """
    mock_get_client = mocker.patch("vinylkit.cli.get_client")
    mock_client = mock_get_client.return_value
    mock_client.rate_limit_info = RateLimitInfo()
    mocker.patch("vinylkit.cli.tag_audio_file")
    mocker.patch("vinylkit.cli.clear_audio_tags")
    mocker.patch("vinylkit.cli.write_release_info")
    mocker.patch("vinylkit.cli.save_artwork")
    return mock_client


def _make_mp3_bytes() -> bytes:
    """Build minimal valid MPEG1 Layer3 audio data (3 frames of silence)."""
    # MPEG1 Layer3 128kbps 44100Hz stereo frame header
    frame_header = bytes([0xFF, 0xFB, 0x90, 0x04])
    frame = frame_header + b"\x00" * 413  # 417-byte frame
    return frame * 3


def _make_flac_bytes() -> bytes:
    """Build minimal valid FLAC file (header + STREAMINFO, no audio frames)."""
    buf = bytearray(b"fLaC")
    buf.append(0x80)  # last-metadata-block flag + type 0 (STREAMINFO)
    buf.extend((34).to_bytes(3, "big"))
    buf.extend(struct.pack(">HH", 4096, 4096))  # min/max block size
    buf.extend(b"\x00" * 6)  # min/max frame size
    # 44100 Hz | 1 channel (0) | 16 bps (15) | 0 total samples
    sr, ch, bps = 44100, 0, 15
    val = (sr << 44) | (ch << 41) | (bps << 36)
    buf.extend(val.to_bytes(8, "big"))
    buf.extend(b"\x00" * 16)  # MD5
    return bytes(buf)


@pytest.fixture
def mp3_file(tmp_path: Path) -> Path:
    """Create a minimal valid MP3 file for tagging tests."""
    p = tmp_path / "test.mp3"
    p.write_bytes(_make_mp3_bytes())
    return p


@pytest.fixture
def flac_file(tmp_path: Path) -> Path:
    """Create a minimal valid FLAC file for tagging tests."""
    p = tmp_path / "test.flac"
    p.write_bytes(_make_flac_bytes())
    return p


def create_mock_release(
    rid: int,
    artist: str,
    title: str,
    *,
    year: int = 2000,
    tracklist: list[TrackInfo] | None = None,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    label: str | None = None,
    catno: str | None = None,
) -> DiscogsRelease:
    """Build a DiscogsRelease with sensible defaults for testing."""
    return DiscogsRelease(
        id=rid,
        artists=[artist],
        title=title,
        year=year,
        tracklist=tracklist or [TrackInfo(position="A1", title="Track 1")],
        labels=[],
        companies=[],
        formats=[],
        identifiers=[],
        extraartists=[],
        genres=genres or [],
        styles=styles or [],
        notes="",
        images=[],
        uri="",
        label=label,
        catno=catno,
    )
