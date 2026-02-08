from __future__ import annotations

import respx
from httpx import Response

from vinylkit.discogs import DiscogsClient, DISCOGS_API_URL


@respx.mock
def test_get_release_success() -> None:
    release_id = 249504
    client = DiscogsClient("key", "secret")
    
    mock_data = {
        "id": release_id,
        "artists": [{"name": "Pink Floyd"}],
        "title": "The Dark Side Of The Moon",
        "year": 1973,
        "labels": [{"name": "Harvest", "catno": "SHVL 804"}],
        "tracklist": [
            {"position": "A1", "title": "Speak To Me"},
            {"position": "A2", "title": "Breathe"}
        ]
    }
    
    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )
    
    release = client.get_release(release_id)
    
    assert release.id == release_id
    assert release.title == "The Dark Side Of The Moon"
    assert "Pink Floyd" in release.artists
    assert len(release.tracklist) == 2
    assert release.tracklist[0].position == "A1"
    assert release.tracklist[0].title == "Speak To Me"


@respx.mock
def test_search_releases_success() -> None:
    query = "Pink Floyd Dark Side"
    client = DiscogsClient("key", "secret")
    
    mock_data = {
        "results": [
            {
                "id": 249504,
                "title": "Pink Floyd - The Dark Side Of The Moon",
                "year": "1973",
                "country": "UK",
                "format": ["Vinyl", "LP", "Album"],
                "label": ["Harvest"]
            }
        ]
    }
    
    respx.get(f"{DISCOGS_API_URL}/database/search").mock(
        return_value=Response(200, json=mock_data)
    )
    
    results = client.search_releases(query)
    
    assert len(results) == 1
    assert results[0]["id"] == 249504
    assert "Dark Side" in results[0]["title"]


@respx.mock
def test_download_image_success() -> None:
    url = "https://example.com/image.jpg"
    client = DiscogsClient("key", "secret")
    
    respx.get(url).mock(return_value=Response(200, content=b"fake image data"))
    
    data = client.download_image(url)
    assert data == b"fake image data"
