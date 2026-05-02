from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, cast

import httpx
from authlib.integrations.httpx_client import OAuth1Client
from loguru import logger
from platformdirs import user_cache_dir

from vinylkit.exceptions import AuthError, DiscogsAPIError
from vinylkit.models import (
    AuthMode,
    CompanyInfo,
    DiscogsRelease,
    ExtraArtistInfo,
    FormatInfo,
    IdentifierInfo,
    ImageInfo,
    LabelInfo,
    RateLimitInfo,
    TrackInfo,
)
from vinylkit.utils import (
    clean_artist_name,
    format_artist_list,
    remove_discogs_disambiguation,
)

DISCOGS_API_URL = "https://api.discogs.com"
REQUEST_TOKEN_URL = f"{DISCOGS_API_URL}/oauth/request_token"
AUTHORIZE_URL = "https://www.discogs.com/oauth/authorize"
ACCESS_TOKEN_URL = f"{DISCOGS_API_URL}/oauth/access_token"
IDENTITY_URL = f"{DISCOGS_API_URL}/oauth/identity"

RATE_LIMIT_DELAY = 1.0  # seconds between requests to stay safe (60 req/min)
APP_NAME = "vinylkit"


def _classify_rate_limit(info: RateLimitInfo) -> tuple[str, float]:
    """Classify current rate limit state into a named tier and delay."""
    if info.limit is None or info.remaining is None:
        return "Fallback", RATE_LIMIT_DELAY
    if info.limit == 0:
        return "Fallback", RATE_LIMIT_DELAY
    remaining_pct = info.remaining / info.limit
    if remaining_pct > 0.33:
        return "Fast", 0.25
    if remaining_pct > 0.15:
        return "Standard", 1.0
    if remaining_pct > 0.08:
        return "Caution", 2.0
    if info.remaining > 0:
        return "Critical", 5.0
    return "Exhausted", 10.0


def describe_throttle_strategy(info: RateLimitInfo) -> str:
    """Return human-readable description of current throttle tier and delay."""
    tier, delay = _classify_rate_limit(info)
    if info.limit is None or info.remaining is None:
        return f"{tier} ({delay}s delay) — no rate limit data available"
    pct = info.remaining / info.limit if info.limit > 0 else 0
    return (
        f"{tier} ({delay}s delay) — {info.remaining}/{info.limit} remaining ({pct:.0%})"
    )


def get_cache_dir() -> Path:
    """Return the platform-appropriate cache directory."""
    return Path(user_cache_dir(APP_NAME))


class DiscogsClient:
    def __init__(
        self,
        consumer_key: str | None = None,
        consumer_secret: str | None = None,
        token: str | None = None,
        secret: str | None = None,
        cache_enabled: bool = True,
        auth_mode: AuthMode = AuthMode.AUTO,
        normalize_discogs_duplicates: bool = True,
    ) -> None:
        self.cache_enabled = cache_enabled
        self.normalize_discogs_duplicates = normalize_discogs_duplicates
        self.cache_dir = get_cache_dir()
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._last_request_time = 0.0
        self.rate_limit_info = RateLimitInfo()
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        user_agent = "VinylKit/0.1.0"

        # Build the correct client once — no throwaway default.
        client: httpx.Client | OAuth1Client
        mode: str

        # 1. Try Full OAuth 1.0a
        if (
            auth_mode in (AuthMode.AUTO, AuthMode.OAUTH)
            and token
            and secret
            and consumer_key
            and consumer_secret
        ):
            mode = "oauth"
            client = OAuth1Client(
                client_id=consumer_key,
                client_secret=consumer_secret,
                token=token,
                token_secret=secret,
                headers={"User-Agent": user_agent},
            )

        # 2. Try Personal Access Token
        elif auth_mode in (AuthMode.AUTO, AuthMode.TOKEN) and token:
            mode = "token"
            client = httpx.Client(
                headers={
                    "Authorization": f"Discogs token={token}",
                    "User-Agent": user_agent,
                }
            )

        # 3. Try Key/Secret (Discogs Auth or Login Prep)
        elif (
            auth_mode in (AuthMode.AUTO, AuthMode.KEY_SECRET, AuthMode.OAUTH)
            and consumer_key
            and consumer_secret
        ):
            mode = "key_secret"
            client = OAuth1Client(
                client_id=consumer_key,
                client_secret=consumer_secret,
                headers={"User-Agent": user_agent},
            )

        # 4. Unauthenticated fallback
        else:
            mode = "none"
            client = httpx.Client(headers={"User-Agent": user_agent})

        self.mode = mode
        self.client = client

    def _get_cache_path(self, release_id: int) -> Path:
        return self.cache_dir / f"release_{release_id}.json"

    def _get_cached_release(self, release_id: int) -> dict[str, Any] | None:
        if not self.cache_enabled:
            return None
        path = self._get_cache_path(release_id)
        if path.exists():
            try:
                return cast("dict[str, Any]", json.loads(path.read_text()))
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to read cache for release {release_id}: {e}")
        return None

    def _cache_release(self, release_id: int, data: dict[str, Any]) -> None:
        if not self.cache_enabled:
            return
        path = self._get_cache_path(release_id)
        try:
            path.write_text(json.dumps(data))
        except OSError as e:
            logger.warning(f"Failed to write cache for release {release_id}: {e}")

    def _update_rate_limit_info(self, resp: httpx.Response) -> None:
        """Extract rate limit headers from a Discogs API response."""
        info = self.rate_limit_info
        limit = resp.headers.get("X-Discogs-Ratelimit")
        used = resp.headers.get("X-Discogs-Ratelimit-Used")
        remaining = resp.headers.get("X-Discogs-Ratelimit-Remaining")

        if limit is not None:
            info.limit = int(limit)
        if used is not None:
            info.used = int(used)
            if info.used > info.peak_used:
                info.peak_used = info.used
        if remaining is not None:
            info.remaining = int(remaining)

        info.last_updated = time.time()

    def _calculate_delay(self) -> float:
        """Calculate request delay based on remaining rate limit headroom."""
        tier, delay = _classify_rate_limit(self.rate_limit_info)
        if tier == "Critical":
            info = self.rate_limit_info
            logger.warning(
                f"Rate limit critical: {info.remaining}/{info.limit} remaining"
            )
        return delay

    def _request_with_retry(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Execute a request with dynamic rate limiting and retry logic.

        Rate-limit (429) responses are retried separately and do not
        consume the error-retry budget used for 5xx / network errors.
        """
        max_error_retries = 3
        max_rate_limit_retries = 3

        error_attempt = 0
        rate_limit_attempt = 0

        while True:
            delay = self._calculate_delay()
            elapsed = time.time() - self._last_request_time
            if elapsed < delay:
                time.sleep(delay - elapsed)
            self._last_request_time = time.time()

            try:
                resp = self.client.request(method, url, **kwargs)  # type: ignore[union-attr]  # OAuth1Client inherits httpx.Client.request at runtime
                self._update_rate_limit_info(resp)
                if resp.status_code == 429:
                    rate_limit_attempt += 1
                    if rate_limit_attempt >= max_rate_limit_retries:
                        raise DiscogsAPIError("Rate limited after maximum retries")
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError as e:
                self._update_rate_limit_info(e.response)
                error_attempt += 1
                if e.response.status_code >= 500 and error_attempt < max_error_retries:
                    logger.warning(
                        f"Server error {e.response.status_code}. Retrying..."
                    )
                    time.sleep(2 ** (error_attempt - 1))
                    continue
                raise DiscogsAPIError(f"Discogs API error: {e}") from e
            except httpx.RequestError as e:
                error_attempt += 1
                if error_attempt < max_error_retries:
                    logger.warning(f"Request failed: {e}. Retrying...")
                    time.sleep(2 ** (error_attempt - 1))
                    continue
                raise DiscogsAPIError(f"Network error: {e}") from e

    def get_authorize_url(self) -> tuple[str, str, str]:
        """Start the OAuth flow."""
        if not isinstance(self.client, OAuth1Client):
            raise AuthError(
                "OAuth client not initialized."
                " Ensure consumer_key and consumer_secret are set."
            )

        try:
            token = self.client.fetch_request_token(REQUEST_TOKEN_URL)
            url = self.client.create_authorization_url(
                AUTHORIZE_URL, token["oauth_token"]
            )
            return url, token["oauth_token"], token["oauth_token_secret"]
        except Exception as e:
            raise AuthError(f"Failed to fetch request token: {e}") from e

    def complete_oauth(
        self, req_token: str, req_token_secret: str, verifier: str
    ) -> tuple[str, str]:
        """Complete OAuth flow."""
        if not isinstance(self.client, OAuth1Client):
            raise AuthError("OAuth client not initialized.")
        try:
            self.client.token = {
                "oauth_token": req_token,
                "oauth_token_secret": req_token_secret,
            }
            token = self.client.fetch_access_token(ACCESS_TOKEN_URL, verifier=verifier)  # type: ignore[no-untyped-call]  # types-authlib stub missing return type
            return token["oauth_token"], token["oauth_token_secret"]
        except Exception as e:
            raise AuthError(f"Failed to fetch access token: {e}") from e

    def get_identity(self) -> dict[str, Any]:
        """Get the authenticated user's full profile identity."""
        logger.debug("Fetching identity")
        resp = self._request_with_retry("GET", IDENTITY_URL)
        identity_data: dict[str, Any] = resp.json()
        username = identity_data.get("username")

        if username:
            try:
                profile_url = f"{DISCOGS_API_URL}/users/{username}"
                profile_resp = self._request_with_retry("GET", profile_url)
                identity_data.update(profile_resp.json())
            except DiscogsAPIError as e:
                logger.warning(f"Could not fetch full profile for {username}: {e}")

        return identity_data

    def get_release(self, release_id: int) -> DiscogsRelease:
        """Fetch and map a Discogs release."""
        logger.debug("Fetching release {}", release_id)
        try:
            data = self._get_cached_release(release_id)
            if data:
                logger.debug("Release {} served from cache", release_id)
            else:
                resp = self._request_with_retry(
                    "GET", f"{DISCOGS_API_URL}/releases/{release_id}"
                )
                data = resp.json()
                self._cache_release(release_id, data)

            tracklist = []
            for t in data.get("tracklist", []):
                if t.get("type_", "track") != "track":
                    continue
                pos = t.get("position", "")
                side = None
                # Handle 1A, 2A prefix
                disc_side_match = re.match(r"^(\d+)([A-Z]+)", pos)
                # Handle A1, AA leading side
                side_match = re.match(r"^([A-Z]+)", pos)

                if disc_side_match:
                    side = disc_side_match.group(2)
                elif side_match:
                    side = side_match.group(1)

                track_extraartists = [
                    ExtraArtistInfo(
                        name=clean_artist_name(
                            a.get("name") or "",
                            a.get("anv") or "",
                            normalize=self.normalize_discogs_duplicates,
                        ),
                        role=a.get("role") or "",
                    )
                    for a in t.get("extraartists", [])
                ]

                # Augment title with featuring artists if present
                featuring = [
                    a.name
                    for a in track_extraartists
                    if a.role.lower() in ("featuring", "feat.", "ft.")
                ]
                title = t.get("title", "")
                if (
                    featuring
                    and "feat." not in title.lower()
                    and "ft." not in title.lower()
                ):
                    feat_str = format_artist_list(featuring)
                    title = f"{title} feat. {feat_str}"

                tracklist.append(
                    TrackInfo(
                        position=pos,
                        title=title,
                        artists=[
                            clean_artist_name(
                                a.get("name") or "",
                                a.get("anv") or "",
                                normalize=self.normalize_discogs_duplicates,
                            )
                            for a in t.get("artists", [])
                        ]
                        if t.get("artists")
                        else [],
                        side=side,
                        extraartists=track_extraartists,
                        duration=t.get("duration") or None,
                    )
                )
            images = [
                ImageInfo(
                    uri=i.get("uri") or "",
                    type=i.get("type") or "",
                    resource_url=i.get("resource_url") or "",
                )
                for i in data.get("images", [])
            ]
            labels_data = [
                LabelInfo(
                    name=remove_discogs_disambiguation(lbl.get("name") or "")
                    if self.normalize_discogs_duplicates
                    else lbl.get("name") or "",
                    catno=lbl.get("catno"),
                )
                for lbl in data.get("labels", [])
            ]
            companies_data = [
                CompanyInfo(
                    name=remove_discogs_disambiguation(comp.get("name") or "")
                    if self.normalize_discogs_duplicates
                    else comp.get("name") or "",
                    entity_type_name=comp.get("entity_type_name") or "",
                )
                for comp in data.get("companies", [])
            ]
            formats_data = [
                FormatInfo(
                    name=f.get("name") or "",
                    qty=f.get("qty") or "1",
                    descriptions=f.get("descriptions", []),
                )
                for f in data.get("formats", [])
            ]
            identifiers_data = [
                IdentifierInfo(
                    type=i.get("type") or "",
                    value=i.get("value") or "",
                    description=i.get("description"),
                )
                for i in data.get("identifiers", [])
            ]
            extraartists_data = [
                ExtraArtistInfo(
                    name=clean_artist_name(
                        a.get("name") or "",
                        a.get("anv") or "",
                        normalize=self.normalize_discogs_duplicates,
                    ),
                    role=a.get("role") or "",
                )
                for a in data.get("extraartists", [])
            ]

            primary_label = labels_data[0] if labels_data else LabelInfo(name="Unknown")

            return DiscogsRelease(
                id=data["id"],
                artists=[
                    clean_artist_name(
                        a.get("name") or "",
                        a.get("anv") or "",
                        normalize=self.normalize_discogs_duplicates,
                    )
                    for a in data.get("artists", [])
                ],
                title=data["title"],
                year=data.get("year"),
                released=data.get("released"),
                country=data.get("country"),
                label=primary_label.name,
                catno=primary_label.catno,
                labels=labels_data,
                companies=companies_data,
                formats=formats_data,
                identifiers=identifiers_data,
                extraartists=extraartists_data,
                genres=data.get("genres", []),
                styles=data.get("styles", []),
                notes=data.get("notes"),
                tracklist=tracklist,
                images=images,
                uri=data.get("uri"),
                master_id=data.get("master_id"),
                master_url=data.get("master_url"),
                artists_sort=remove_discogs_disambiguation(
                    data.get("artists_sort") or ""
                )
                if self.normalize_discogs_duplicates and data.get("artists_sort")
                else data.get("artists_sort"),
                data_quality=data.get("data_quality"),
                format_quantity=data.get("format_quantity"),
            )
        except DiscogsAPIError:
            raise
        except Exception as e:
            raise DiscogsAPIError(f"Error mapping release data: {e}") from e

    def search_releases(
        self, query: str | None = None, **filters: Any
    ) -> list[dict[str, Any]]:
        """Search releases with optional filters (artist, release_title, etc.)."""
        logger.debug("Searching releases: query={}", query)
        params: list[tuple[str, Any]] = [("type", "release")]
        if query:
            params.append(("q", query))

        # Map 'album' to 'release_title' if provided
        if "album" in filters:
            filters["release_title"] = filters.pop("album")

        for key, value in filters.items():
            if value is None:
                continue
            if isinstance(value, list):
                params.extend((key, v) for v in value)
            else:
                params.append((key, value))

        resp = self._request_with_retry(
            "GET",
            f"{DISCOGS_API_URL}/database/search",
            params=params,
        )
        return cast("list[dict[str, Any]]", resp.json().get("results", []))

    def download_image(self, url: str) -> bytes:
        """Download image."""
        logger.debug("Downloading image")
        resp = self._request_with_retry("GET", url)
        return resp.content

    def get_collection_releases(
        self, username: str, folder_id: int = 0
    ) -> list[dict[str, Any]]:
        """Fetch all releases in a user's collection folder."""
        logger.debug("Fetching collection for user: {}", username)
        releases = []
        page = 1
        per_page = 100

        while True:
            url = (
                f"{DISCOGS_API_URL}/users/{username}"
                f"/collection/folders/{folder_id}/releases"
            )
            resp = self._request_with_retry(
                "GET", url, params={"page": page, "per_page": per_page}
            )
            data = resp.json()
            releases.extend(data.get("releases", []))

            pagination = data.get("pagination", {})
            if page >= pagination.get("pages", 1):
                break
            page += 1

        return releases
