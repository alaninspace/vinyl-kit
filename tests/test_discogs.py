from __future__ import annotations

import respx
from httpx import Response

from vinylkit.discogs import DISCOGS_API_URL, RATE_LIMIT_DELAY, DiscogsClient


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
            {"position": "A2", "title": "Breathe"},
        ],
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
                "label": ["Harvest"],
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
def test_search_releases_with_filters() -> None:
    client = DiscogsClient("key", "secret")

    mock_data = {"results": [{"id": 123, "title": "Green Velvet - Flash"}]}

    # Verify that params are passed correctly
    route = respx.get(f"{DISCOGS_API_URL}/database/search").mock(
        return_value=Response(200, json=mock_data)
    )

    results = client.search_releases(
        artist="Green Velvet", album="Flash", format=["Vinyl", "CD"]
    )

    assert len(results) == 1
    # Check the call included mapped release_title and format filters
    # When multiple params with same key exist, check URL string
    url_str = str(route.calls.last.request.url)
    assert "format=Vinyl" in url_str
    assert "format=CD" in url_str
    assert "artist=Green+Velvet" in url_str
    assert "release_title=Flash" in url_str


@respx.mock
def test_download_image_success() -> None:
    url = "https://example.com/image.jpg"
    client = DiscogsClient("key", "secret")

    respx.get(url).mock(return_value=Response(200, content=b"fake image data"))

    data = client.download_image(url)
    assert data == b"fake image data"


@respx.mock
def test_get_collection_releases_pagination() -> None:
    username = "testuser"
    client = DiscogsClient("key", "secret")

    # Mock page 1
    respx.get(f"{DISCOGS_API_URL}/users/{username}/collection/folders/0/releases").mock(
        side_effect=[
            Response(
                200,
                json={"releases": [{"id": 1}], "pagination": {"pages": 2, "page": 1}},
            ),
            Response(
                200,
                json={"releases": [{"id": 2}], "pagination": {"pages": 2, "page": 2}},
            ),
        ]
    )

    releases = client.get_collection_releases(username)

    assert len(releases) == 2
    assert releases[0]["id"] == 1
    assert releases[1]["id"] == 2


# --- Rate Limit Tests ---

RATE_LIMIT_HEADERS = {
    "X-Discogs-Ratelimit": "60",
    "X-Discogs-Ratelimit-Used": "15",
    "X-Discogs-Ratelimit-Remaining": "45",
}


@respx.mock
def test_rate_limit_headers_captured() -> None:
    """Verify rate limit headers are extracted from a successful response."""
    client = DiscogsClient("key", "secret")
    url = "https://example.com/image.jpg"

    respx.get(url).mock(
        return_value=Response(200, content=b"data", headers=RATE_LIMIT_HEADERS)
    )

    client.download_image(url)

    info = client.rate_limit_info
    assert info.limit == 60
    assert info.used == 15
    assert info.remaining == 45
    assert info.last_updated > 0


@respx.mock
def test_rate_limit_peak_tracking() -> None:
    """Verify peak_used tracks the high-water mark across requests."""
    client = DiscogsClient("key", "secret")
    url = "https://example.com/image.jpg"

    # First request: used=10
    respx.get(url).mock(
        side_effect=[
            Response(
                200,
                content=b"d1",
                headers={
                    "X-Discogs-Ratelimit": "60",
                    "X-Discogs-Ratelimit-Used": "10",
                    "X-Discogs-Ratelimit-Remaining": "50",
                },
            ),
            Response(
                200,
                content=b"d2",
                headers={
                    "X-Discogs-Ratelimit": "60",
                    "X-Discogs-Ratelimit-Used": "25",
                    "X-Discogs-Ratelimit-Remaining": "35",
                },
            ),
            Response(
                200,
                content=b"d3",
                headers={
                    "X-Discogs-Ratelimit": "60",
                    "X-Discogs-Ratelimit-Used": "12",
                    "X-Discogs-Ratelimit-Remaining": "48",
                },
            ),
        ]
    )

    client.download_image(url)
    client.download_image(url)
    client.download_image(url)

    assert client.rate_limit_info.peak_used == 25
    assert client.rate_limit_info.used == 12


@respx.mock
def test_rate_limit_missing_headers() -> None:
    """Graceful handling when rate limit headers are absent."""
    client = DiscogsClient("key", "secret")
    url = "https://example.com/image.jpg"

    respx.get(url).mock(return_value=Response(200, content=b"data"))

    client.download_image(url)

    info = client.rate_limit_info
    assert info.limit is None
    assert info.used is None
    assert info.remaining is None


@respx.mock
def test_rate_limit_headers_captured_on_429() -> None:
    """Verify rate limit headers are captured even on 429 responses."""
    client = DiscogsClient("key", "secret", cache_enabled=False)
    release_id = 999

    headers_429 = {
        "X-Discogs-Ratelimit": "60",
        "X-Discogs-Ratelimit-Used": "60",
        "X-Discogs-Ratelimit-Remaining": "0",
        "Retry-After": "1",
    }
    headers_ok = {
        "X-Discogs-Ratelimit": "60",
        "X-Discogs-Ratelimit-Used": "1",
        "X-Discogs-Ratelimit-Remaining": "59",
    }
    mock_data = {
        "id": release_id,
        "artists": [{"name": "Test"}],
        "title": "T",
        "tracklist": [],
    }

    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        side_effect=[
            Response(429, headers=headers_429),
            Response(200, json=mock_data, headers=headers_ok),
        ]
    )

    release = client.get_release(release_id)
    assert release.id == release_id
    # Peak should reflect the 429 response (used=60)
    assert client.rate_limit_info.peak_used == 60
    # Final state should reflect the 200 response
    assert client.rate_limit_info.used == 1


def test_calculate_delay_no_data() -> None:
    """Fallback to RATE_LIMIT_DELAY when no rate limit data available."""
    client = DiscogsClient("key", "secret")
    assert client._calculate_delay() == RATE_LIMIT_DELAY


def test_calculate_delay_fast_tier() -> None:
    """> 33% remaining => 0.25s delay."""
    client = DiscogsClient("key", "secret")
    info = client.rate_limit_info
    info.limit = 60
    info.remaining = 40  # 67%
    assert client._calculate_delay() == 0.25


def test_calculate_delay_standard_tier() -> None:
    """15-33% remaining => 1.0s delay."""
    client = DiscogsClient("key", "secret")
    info = client.rate_limit_info
    info.limit = 60
    info.remaining = 12  # 20%
    assert client._calculate_delay() == 1.0


def test_calculate_delay_caution_tier() -> None:
    """8-15% remaining => 2.0s delay."""
    client = DiscogsClient("key", "secret")
    info = client.rate_limit_info
    info.limit = 60
    info.remaining = 6  # 10%
    assert client._calculate_delay() == 2.0


def test_calculate_delay_critical_tier() -> None:
    """1-8% remaining => 5.0s delay."""
    client = DiscogsClient("key", "secret")
    info = client.rate_limit_info
    info.limit = 60
    info.remaining = 2  # 3.3%
    assert client._calculate_delay() == 5.0


def test_calculate_delay_exhausted() -> None:
    """0% remaining => 10.0s delay."""
    client = DiscogsClient("key", "secret")
    info = client.rate_limit_info
    info.limit = 60
    info.remaining = 0
    assert client._calculate_delay() == 10.0


def test_calculate_delay_unauthenticated_limit() -> None:
    """Unauthenticated 25 req/min limit should still apply tiers correctly."""
    client = DiscogsClient("key", "secret")
    info = client.rate_limit_info
    info.limit = 25
    info.remaining = 10  # 40% -> fast tier
    assert client._calculate_delay() == 0.25

    info.remaining = 5  # 20% -> standard tier
    assert client._calculate_delay() == 1.0

    info.remaining = 3  # 12% -> caution tier
    assert client._calculate_delay() == 2.0
