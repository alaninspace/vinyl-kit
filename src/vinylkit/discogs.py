from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import httpx
from authlib.integrations.httpx_client import OAuth1Client
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
    TrackInfo,
)

logger = logging.getLogger(__name__)

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
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        user_agent = "VinylKit/0.1.0"

        # Initialize Default (None)
        self.mode = "none"
        self.client: httpx.Client | OAuth1Client = httpx.Client(
            headers={"User-Agent": user_agent}
        )

        # 1. Try Full OAuth 1.0a
        if auth_mode in ("auto", "oauth"):
            if token and secret and consumer_key and consumer_secret:
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
        if auth_mode in ("auto", "token"):
            if token:
                self.mode = "token"
                self.client = httpx.Client(
                    headers={
                        "Authorization": f"Discogs token={token}",
                        "User-Agent": user_agent,
                    }
                )
                return

        # 3. Try Key/Secret (Discogs Auth or Login Prep)
        if auth_mode in (
            "auto",
            "key_secret",
            "oauth",
        ):  # oauth falls back here if no token yet
            if consumer_key and consumer_secret:
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
                return json.loads(path.read_text())
            except Exception as e:
                logger.warning(f"Failed to read cache for release {release_id}: {e}")
        return None

    def _cache_release(self, release_id: int, data: dict[str, Any]) -> None:
        if not self.cache_enabled:
            return
        path = self._get_cache_path(release_id)
        try:
            path.write_text(json.dumps(data))
        except Exception as e:
            logger.warning(f"Failed to write cache for release {release_id}: {e}")

    def _wait_for_rate_limit(self) -> None:
        """Ensure we don't exceed the 60 requests per minute limit."""
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _request_with_retry(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Execute a request with rate limiting and basic retry logic."""
        for attempt in range(3):
            self._wait_for_rate_limit()
            try:
                resp = self.client.request(method, url, **kwargs)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError as e:
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
                "OAuth client not initialized. Ensure consumer_key and consumer_secret are set."
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
        identity_data = resp.json()
        username = identity_data.get("username")

        if username:
            try:
                profile_url = f"{DISCOGS_API_URL}/users/{username}"
                profile_resp = self._request_with_retry("GET", profile_url)
                identity_data.update(profile_resp.json())
            except Exception as e:
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

    def search_releases(self, query: str) -> list[dict[str, Any]]:
        """Search releases."""
        resp = self._request_with_retry(
            "GET",
            f"{DISCOGS_API_URL}/database/search",
            params={"q": query, "type": "release"},
        )
        return resp.json().get("results", [])

    def download_image(self, url: str) -> bytes:
        """Download image."""
        resp = self._request_with_retry("GET", url)
        return resp.content
