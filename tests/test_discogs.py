from __future__ import annotations

import pytest
import respx
from httpx import Response

from vinylkit.discogs import (
    DISCOGS_API_URL,
    RATE_LIMIT_DELAY,
    DiscogsClient,
    describe_throttle_strategy,
)
from vinylkit.exceptions import DiscogsAPIError
from vinylkit.models import RateLimitInfo


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
def test_get_release_new_fields() -> None:
    """Verify master_id, artists_sort, data_quality, format_quantity are parsed."""
    release_id = 12345
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "Test Artist"}],
        "title": "Test Album",
        "year": 2020,
        "tracklist": [
            {
                "position": "A1",
                "title": "Track 1",
                "duration": "5:32",
                "extraartists": [{"name": "Mixer", "role": "Remix"}],
            },
        ],
        "master_id": 9999,
        "master_url": "https://api.discogs.com/masters/9999",
        "artists_sort": "Test Artist, The",
        "data_quality": "Correct",
        "format_quantity": 2,
    }

    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)

    assert release.master_id == 9999
    assert release.master_url == "https://api.discogs.com/masters/9999"
    assert release.artists_sort == "Test Artist, The"
    assert release.data_quality == "Correct"
    assert release.format_quantity == 2
    # Track-level extraartists and duration
    assert release.tracklist[0].duration == "5:32"
    assert len(release.tracklist[0].extraartists) == 1
    assert release.tracklist[0].extraartists[0].name == "Mixer"
    assert release.tracklist[0].extraartists[0].role == "Remix"


@respx.mock
def test_get_release_empty_duration_is_none() -> None:
    """Empty string duration should be normalized to None."""
    release_id = 11111
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "A"}],
        "title": "T",
        "tracklist": [{"position": "A1", "title": "T1", "duration": ""}],
    }

    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)
    assert release.tracklist[0].duration is None


@respx.mock
def test_get_release_featuring_augmentation() -> None:
    """Verify that Featuring artists are appended to the track title."""
    release_id = 314929
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "Darkanoid"}, {"name": "DJ KC (2)"}],
        "title": "The Darker Thoughts E.P.",
        "tracklist": [
            {
                "position": "B",
                "title": "Smoke The Weed",
                "extraartists": [
                    {"name": "Federal (2)", "role": "Featuring"},
                    {"name": "Killasound", "role": "Featuring"},
                ],
            },
        ],
    }

    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)

    # Note: DJ KC (2) and Federal (2) should be normalized if
    # normalization is on (default True).
    # format_artist_list(Federal, Killasound) -> Federal & Killasound
    assert release.tracklist[0].title == "Smoke The Weed feat. Federal & Killasound"


@respx.mock
def test_get_release_featuring_no_duplicate() -> None:
    """Verify that featuring artists are not appended if already in the title."""
    release_id = 999
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "Artist"}],
        "title": "Album",
        "tracklist": [
            {
                "position": "1",
                "title": "Track feat. Other",
                "extraartists": [{"name": "Other", "role": "Featuring"}],
            },
        ],
    }

    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)

    assert release.tracklist[0].title == "Track feat. Other"


@respx.mock
def test_get_release_skips_headings() -> None:
    """Tracklist entries with type_ 'heading' should be excluded."""
    release_id = 43598
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "Peace Division"}],
        "title": "Do You See Me?",
        "tracklist": [
            {"position": "", "type_": "heading", "title": "This"},
            {"position": "A", "type_": "track", "title": "Original Mix"},
            {"position": "", "type_": "heading", "title": "That"},
            {"position": "B", "type_": "track", "title": "Shh Remix"},
        ],
    }

    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)
    assert len(release.tracklist) == 2
    assert release.tracklist[0].title == "Original Mix"
    assert release.tracklist[1].title == "Shh Remix"


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


# --- describe_throttle_strategy Tests ---


def test_describe_throttle_strategy_no_data() -> None:
    """Fallback tier when no rate limit data is available."""
    info = RateLimitInfo()
    result = describe_throttle_strategy(info)
    assert "Fallback" in result
    assert "1.0s delay" in result
    assert "no rate limit data available" in result


def test_describe_throttle_strategy_fast_tier() -> None:
    """Fast tier when > 33% remaining."""
    info = RateLimitInfo()
    info.limit = 60
    info.remaining = 55
    result = describe_throttle_strategy(info)
    assert "Fast" in result
    assert "0.25s" in result
    assert "55/60" in result


def test_describe_throttle_strategy_standard_tier() -> None:
    """Standard tier when 15-33% remaining."""
    info = RateLimitInfo()
    info.limit = 60
    info.remaining = 12
    result = describe_throttle_strategy(info)
    assert "Standard" in result
    assert "1.0s" in result


def test_describe_throttle_strategy_caution_tier() -> None:
    """Caution tier when 8-15% remaining."""
    info = RateLimitInfo()
    info.limit = 60
    info.remaining = 6
    result = describe_throttle_strategy(info)
    assert "Caution" in result
    assert "2.0s" in result


def test_describe_throttle_strategy_critical_tier() -> None:
    """Critical tier when 1-8% remaining."""
    info = RateLimitInfo()
    info.limit = 60
    info.remaining = 2
    result = describe_throttle_strategy(info)
    assert "Critical" in result
    assert "5.0s" in result


def test_describe_throttle_strategy_exhausted() -> None:
    """Exhausted tier when 0 remaining."""
    info = RateLimitInfo()
    info.limit = 60
    info.remaining = 0
    result = describe_throttle_strategy(info)
    assert "Exhausted" in result
    assert "10.0s" in result


# ---------------------------------------------------------------------------
# None fallbacks in model construction from API data
# ---------------------------------------------------------------------------


@respx.mock
def test_missing_image_fields_default_to_empty() -> None:
    """Fields missing from API JSON should fall back to empty strings."""
    release_id = 55555
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "A"}],
        "title": "T",
        "tracklist": [],
        "images": [{}],
    }
    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)
    img = release.images[0]
    assert img.uri == ""
    assert img.type == ""
    assert img.resource_url == ""


@respx.mock
def test_missing_format_qty_defaults_to_one() -> None:
    release_id = 55556
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "A"}],
        "title": "T",
        "tracklist": [],
        "formats": [{"name": "Vinyl"}],
    }
    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)
    assert release.formats[0].qty == "1"
    assert release.formats[0].name == "Vinyl"


@respx.mock
def test_missing_company_fields_default_to_empty() -> None:
    release_id = 55557
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "A"}],
        "title": "T",
        "tracklist": [],
        "companies": [{}],
    }
    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)
    assert release.companies[0].name == ""
    assert release.companies[0].entity_type_name == ""


@respx.mock
def test_missing_extraartist_fields_default_to_empty() -> None:
    release_id = 55558
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "A"}],
        "title": "T",
        "tracklist": [
            {
                "position": "A1",
                "title": "T1",
                "extraartists": [{}],
            }
        ],
        "extraartists": [{}],
    }
    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)
    assert release.extraartists[0].name == ""
    assert release.extraartists[0].role == ""
    assert release.tracklist[0].extraartists[0].name == ""
    assert release.tracklist[0].extraartists[0].role == ""


@respx.mock
def test_missing_identifier_fields_default_to_empty() -> None:
    release_id = 55559
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "A"}],
        "title": "T",
        "tracklist": [],
        "identifiers": [{}],
    }
    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)
    assert release.identifiers[0].type == ""
    assert release.identifiers[0].value == ""


# ---------------------------------------------------------------------------
# 429 retry budget separation
# ---------------------------------------------------------------------------


@respx.mock
def test_429_then_success() -> None:
    """A 429 followed by a 200 should succeed."""
    release_id = 77777
    client = DiscogsClient("key", "secret", cache_enabled=False)

    mock_data = {
        "id": release_id,
        "artists": [{"name": "Test"}],
        "title": "T",
        "tracklist": [],
    }

    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        side_effect=[
            Response(429, headers={"Retry-After": "0"}),
            Response(200, json=mock_data),
        ]
    )

    release = client.get_release(release_id)
    assert release.id == release_id


@respx.mock
def test_429_does_not_consume_error_budget() -> None:
    """429s should not prevent retrying a subsequent 500."""
    client = DiscogsClient("key", "secret", cache_enabled=False)
    url = "https://example.com/test"

    respx.get(url).mock(
        side_effect=[
            Response(429, headers={"Retry-After": "0"}),
            Response(429, headers={"Retry-After": "0"}),
            Response(500),
            Response(200, content=b"ok"),
        ]
    )

    resp = client._request_with_retry("GET", url)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Artist name cleaning: disambiguation suffixes and anv
# ---------------------------------------------------------------------------


@respx.mock
def test_artist_disambiguation_stripped() -> None:
    """Artist name like 'Pariah (2)' should be cleaned to 'Pariah'."""
    release_id = 92086
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "Pariah (2)", "anv": ""}],
        "title": "Test",
        "tracklist": [],
    }
    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)
    assert release.artists == ["Pariah"]


@respx.mock
def test_artist_anv_takes_priority() -> None:
    """When anv is set, it should be used instead of the raw name."""
    release_id = 92087
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "Andy Page", "anv": "Android Page"}],
        "title": "Test",
        "tracklist": [],
    }
    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)
    assert release.artists == ["Android Page"]


@respx.mock
def test_extraartist_disambiguation_stripped() -> None:
    """Extraartist with disambiguation suffix should be cleaned."""
    release_id = 92088
    client = DiscogsClient("key", "secret")

    mock_data = {
        "id": release_id,
        "artists": [{"name": "A"}],
        "title": "Test",
        "tracklist": [],
        "extraartists": [{"name": "Nicolai (2)", "anv": "", "role": "Producer"}],
    }
    respx.get(f"{DISCOGS_API_URL}/releases/{release_id}").mock(
        return_value=Response(200, json=mock_data)
    )

    release = client.get_release(release_id)
    assert release.extraartists[0].name == "Nicolai"
    assert release.extraartists[0].role == "Producer"


@respx.mock
def test_exhausted_429_retries_raises() -> None:
    """Three consecutive 429s should raise a rate-limit error."""
    client = DiscogsClient("key", "secret", cache_enabled=False)
    url = "https://example.com/test"

    respx.get(url).mock(
        side_effect=[
            Response(429, headers={"Retry-After": "0"}),
            Response(429, headers={"Retry-After": "0"}),
            Response(429, headers={"Retry-After": "0"}),
        ]
    )

    with pytest.raises(DiscogsAPIError, match="Rate limited"):
        client._request_with_retry("GET", url)
