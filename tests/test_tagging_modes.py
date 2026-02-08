from __future__ import annotations

from pathlib import Path
import pytest
from mutagen.id3 import ID3, TIT2
from mutagen.mp3 import MP3
from vinylkit.models import DiscogsRelease, TrackInfo, TagMode
from vinylkit.tagging import tag_audio_file

@pytest.fixture
def mp3_with_tags(tmp_path: Path) -> Path:
    p = tmp_path / "test.mp3"
    # Create a dummy MP3 with a tag
    audio = MP3() # This won't work without a real file structure, better mock
    return p

def test_tag_mode_replace_clears_tags(tmp_path: Path, mocker):
    p = tmp_path / "test.mp3"
    p.write_bytes(b"empty") # Dummy file
    
    # Mock mutagen
    mock_mp3_class = mocker.patch("vinylkit.tagging.MP3")
    mock_audio = mock_mp3_class.return_value
    mock_audio.tags = mocker.Mock(spec=ID3)
    
    release = DiscogsRelease(id=1, artists=["A"], title="T", tracklist=[TrackInfo("1", "T1")])
    
    tag_audio_file(p, release, 0, tag_mode=TagMode.REPLACE)
    
    # Verify delete was called
    assert mock_audio.delete.called

def test_tag_mode_merge_keeps_tags(tmp_path: Path, mocker):
    p = tmp_path / "test.mp3"
    p.write_bytes(b"empty")
    
    # Mock mutagen
    mock_mp3_class = mocker.patch("vinylkit.tagging.MP3")
    mock_audio = mock_mp3_class.return_value
    mock_audio.tags = mocker.Mock(spec=ID3)
    
    release = DiscogsRelease(id=1, artists=["A"], title="T", tracklist=[TrackInfo("1", "T1")])
    
    tag_audio_file(p, release, 0, tag_mode=TagMode.MERGE)
    
    # Verify delete was NOT called
    assert not mock_audio.delete.called
