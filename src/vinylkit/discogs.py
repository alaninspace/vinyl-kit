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

DISCOGS_API_URL = "https://api.discogs.com"
REQUEST_TOKEN_URL = f"{DISCOGS_API_URL}/oauth/request_token"
AUTHORIZE_URL = "https://www.discogs.com/oauth/authorize"
ACCESS_TOKEN_URL = f"{DISCOGS_API_URL}/oauth/access_token"
IDENTITY_URL = f"{DISCOGS_API_URL}/oauth/identity"

RATE_LIMIT_DELAY = 1.0  # seconds between requests to stay safe (60 req/min)
APP_NAME = "vinylkit"


class DiscogsClient:
    def __init__(
        self,
        consumer_key: str | None = None,
        consumer_secret: str | None = None,
        token: str | None = None,
        secret: str | None = None,
        cache_enabled: bool = True,
        auth_mode: str = "auto",
    ) -> None:
        self.cache_enabled = cache_enabled
        self.cache_dir = Path(user_cache_dir(APP_NAME))
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._last_request_time = 0.0
        self.rate_limit_info = RateLimitInfo()
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        user_agent = "VinylKit/0.1.0"

        # Initialize Default (None)
        self.mode = "none"
        self.client: httpx.Client | OAuth1Client = httpx.Client(
            headers={"User-Agent": user_agent}
        )

        # 1. Try Full OAuth 1.0a
        if (
            auth_mode in ("auto", "oauth")
            and token
            and secret
            and consumer_key
            and consumer_secret
        ):
            self.mode = "oauth"
            self.client = OAuth1Client(
                client_id=consumer_key,
                client_secret=consumer_secret,
                token=token,
                token_secret=secret,
                headers={"User-Agent": user_agent},
            )
            return

        # 2. Try Personal Access Token
        if auth_mode in ("auto", "token") and token:
            self.mode = "token"
            self.client = httpx.Client(
                headers={
                    "Authorization": f"Discogs token={token}",
                    "User-Agent": user_agent,
                }
            )
            return

        # 3. Try Key/Secret (Discogs Auth or Login Prep)
        if (
            auth_mode in ("auto", "key_secret", "oauth")
            and consumer_key
            and consumer_secret
        ):
            self.mode = "key_secret"
            self.client = OAuth1Client(
                client_id=consumer_key,
                client_secret=consumer_secret,
                headers={"User-Agent": user_agent},
            )
            return

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
        info = self.rate_limit_info
        if info.limit is None or info.remaining is None:
            return RATE_LIMIT_DELAY  # 1.0s fallback when no data

        if info.limit == 0:
            return RATE_LIMIT_DELAY

        remaining_pct = info.remaining / info.limit

        if remaining_pct > 0.33:
            return 0.25
        if remaining_pct > 0.15:
            return 1.0
        if remaining_pct > 0.08:
            return 2.0
        if info.remaining > 0:
            logger.warning(
                f"Rate limit critical: {info.remaining}/{info.limit} remaining"
            )
            return 5.0
        return 10.0  # exhausted

    def _request_with_retry(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Execute a request with dynamic rate limiting and retry logic."""
        for attempt in range(3):
            delay = self._calculate_delay()
            elapsed = time.time() - self._last_request_time
            if elapsed < delay:
                time.sleep(delay - elapsed)
            self._last_request_time = time.time()

            try:
                resp = self.client.request(method, url, **kwargs)
                self._update_rate_limit_info(resp)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError as e:
                self._update_rate_limit_info(e.response)
                if e.response.status_code >= 500 and attempt < 2:
                    logger.warning(
                        f"Server error {e.response.status_code}. Retrying..."
                    )
                    time.sleep(2**attempt)
                    continue
                raise DiscogsAPIError(f"Discogs API error: {e}") from e
            except httpx.RequestError as e:
                if attempt < 2:
                    logger.warning(f"Request failed: {e}. Retrying...")
                    time.sleep(2**attempt)
                    continue
                raise DiscogsAPIError(f"Network error: {e}") from e
        raise DiscogsAPIError("Failed after maximum retries")

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
            token = self.client.fetch_access_token(ACCESS_TOKEN_URL, verifier=verifier)
            return token["oauth_token"], token["oauth_token_secret"]
        except Exception as e:
            raise AuthError(f"Failed to fetch access token: {e}") from e

    def get_identity(self) -> dict[str, Any]:
        """Get the authenticated user's full profile identity."""
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
        try:
            data = self._get_cached_release(release_id)
            if not data:
                resp = self._request_with_retry(
                    "GET", f"{DISCOGS_API_URL}/releases/{release_id}"
                )
                data = resp.json()
                self._cache_release(release_id, data)

            tracklist = []
            for t in data.get("tracklist", []):
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

                tracklist.append(
                    TrackInfo(
                        position=pos,
                        title=t.get("title", ""),
                        artists=[a.get("name") for a in t.get("artists", [])]
                        if t.get("artists")
                        else [],
                        side=side,
                    )
                )
            images = [
                ImageInfo(
                    uri=i.get("uri"),
                    type=i.get("type"),
                    resource_url=i.get("resource_url"),
                )
                for i in data.get("images", [])
            ]
            labels_data = [
                LabelInfo(name=lbl.get("name"), catno=lbl.get("catno"))
                for lbl in data.get("labels", [])
            ]
            companies_data = [
                CompanyInfo(
                    name=comp.get("name"), entity_type_name=comp.get("entity_type_name")
                )
                for comp in data.get("companies", [])
            ]
            formats_data = [
                FormatInfo(
                    name=f.get("name"),
                    qty=f.get("qty"),
                    descriptions=f.get("descriptions", []),
                )
                for f in data.get("formats", [])
            ]
            identifiers_data = [
                IdentifierInfo(
                    type=i.get("type"),
                    value=i.get("value"),
                    description=i.get("description"),
                )
                for i in data.get("identifiers", [])
            ]
            extraartists_data = [
                ExtraArtistInfo(name=a.get("name"), role=a.get("role"))
                for a in data.get("extraartists", [])
            ]

            primary_label = labels_data[0] if labels_data else LabelInfo(name="Unknown")

            return DiscogsRelease(
                id=data["id"],
                artists=[a.get("name") for a in data.get("artists", [])],
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
            )
        except DiscogsAPIError:
            raise
        except Exception as e:
            raise DiscogsAPIError(f"Error mapping release data: {e}") from e

    def search_releases(
        self, query: str | None = None, **filters: Any
    ) -> list[dict[str, Any]]:
        """Search releases with optional filters (artist, release_title, etc.)."""
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
        resp = self._request_with_retry("GET", url)
        return resp.content

    def get_collection_releases(
        self, username: str, folder_id: int = 0
    ) -> list[dict[str, Any]]:
        """Fetch all releases in a user's collection folder."""
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
