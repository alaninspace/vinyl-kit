from __future__ import annotations

import subprocess
import sys

import httpx
import respx

from vinylkit.discogs import (
    ACCESS_TOKEN_URL,
    REQUEST_TOKEN_URL,
    DiscogsClient,
    OAuth1Auth,
)
from vinylkit.models import AuthMode


def test_auth_mode_auto_prioritizes_oauth():
    # If all keys are present, auto should pick oauth
    client = DiscogsClient(
        consumer_key="ck",
        consumer_secret="cs",
        token="t",
        secret="s",
        auth_mode=AuthMode.AUTO,
    )
    assert client.mode == "oauth"
    assert isinstance(client.client, httpx.Client)
    assert isinstance(client.client.auth, OAuth1Auth)
    assert client.oauth is not None


def test_auth_mode_auto_falls_back_to_token():
    # If no secret, auto should pick token
    client = DiscogsClient(
        consumer_key="ck", consumer_secret="cs", token="t", auth_mode=AuthMode.AUTO
    )
    assert client.mode == "token"
    # Token mode uses standard httpx.Client with headers
    assert isinstance(client.client, httpx.Client)
    assert client.client.headers["Authorization"] == "Discogs token=t"
    assert client.oauth is None


def test_auth_mode_auto_falls_back_to_key_secret():
    # If only consumer keys, auto should pick key_secret
    client = DiscogsClient(
        consumer_key="ck", consumer_secret="cs", auth_mode=AuthMode.AUTO
    )
    assert client.mode == "key_secret"
    # key_secret keeps an OAuth session (needed for login flow)
    assert isinstance(client.client.auth, OAuth1Auth)
    assert client.oauth is not None


def test_auth_mode_force_token():
    # Even if oauth keys are present, force token mode
    client = DiscogsClient(
        consumer_key="ck",
        consumer_secret="cs",
        token="t",
        secret="s",
        auth_mode=AuthMode.TOKEN,
    )
    assert client.mode == "token"
    assert isinstance(client.client, httpx.Client)
    assert client.client.headers["Authorization"] == "Discogs token=t"


def test_auth_mode_force_oauth_fails_if_missing_keys():
    # If we force oauth but lack tokens, it should fall back to auto logic or none
    # In our current implementation, it skips the oauth block and tries token
    client = DiscogsClient(
        consumer_key="ck", consumer_secret="cs", auth_mode=AuthMode.OAUTH
    )
    # Since it can't do oauth, it continues to try key_secret (auto-logic fallback)
    assert client.mode == "key_secret"


def test_auth_mode_none():
    client = DiscogsClient()
    assert client.mode == "none"
    assert isinstance(client.client, httpx.Client)
    assert "Authorization" not in client.client.headers


# ---------------------------------------------------------------------------
# Single-client construction (no throwaway default)
# ---------------------------------------------------------------------------


def test_oauth_mode_sets_oauth():
    client = DiscogsClient("ck", "cs", token="t", secret="s", cache_enabled=False)
    assert client.mode == "oauth"


def test_token_mode_sets_token():
    client = DiscogsClient(token="t", cache_enabled=False)
    assert client.mode == "token"


def test_key_secret_mode_sets_key_secret():
    client = DiscogsClient("ck", "cs", cache_enabled=False)
    assert client.mode == "key_secret"


def test_no_creds_sets_none():
    client = DiscogsClient(cache_enabled=False)
    assert client.mode == "none"


def test_forced_auth_mode_token_ignores_oauth_creds():
    """When auth_mode=AuthMode.TOKEN, full OAuth creds should not trigger oauth."""
    client = DiscogsClient(
        "ck",
        "cs",
        token="t",
        secret="s",
        auth_mode=AuthMode.TOKEN,
        cache_enabled=False,
    )
    assert client.mode == "token"


# ---------------------------------------------------------------------------
# OAuth signing without authlib's httpx integration
# ---------------------------------------------------------------------------


def test_importing_vinylkit_does_not_load_authlib_httpx_integration():
    """authlib's httpx_client prints a deprecation warning (httpx -> httpx2)."""
    code = (
        "import sys, warnings\n"
        "warnings.simplefilter('always')\n"
        "with warnings.catch_warnings(record=True) as caught:\n"
        "    import vinylkit.cli, vinylkit.discogs\n"
        "assert 'authlib.integrations.httpx_client' not in sys.modules\n"
        "bad = [w for w in caught if 'httpx2' in str(w.message)]\n"
        "assert not bad, bad\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "httpx2" not in result.stderr


@respx.mock
def test_oauth_requests_are_signed():
    route = respx.get("https://api.discogs.com/oauth/identity").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )
    client = DiscogsClient("ck", "cs", token="t", secret="s", cache_enabled=False)
    client.get_identity()

    auth_header = route.calls.last.request.headers["Authorization"]
    assert auth_header.startswith("OAuth ")
    assert 'oauth_consumer_key="ck"' in auth_header
    assert 'oauth_token="t"' in auth_header
    assert "oauth_signature=" in auth_header


@respx.mock
def test_oauth_login_flow_fetches_and_signs_tokens():
    request_route = respx.post(REQUEST_TOKEN_URL).mock(
        return_value=httpx.Response(200, text="oauth_token=rt&oauth_token_secret=rts")
    )
    access_route = respx.post(ACCESS_TOKEN_URL).mock(
        return_value=httpx.Response(200, text="oauth_token=at&oauth_token_secret=ats")
    )
    client = DiscogsClient("ck", "cs", cache_enabled=False)

    url, req_token, req_secret = client.get_authorize_url()
    assert "oauth_token=rt" in url
    assert (req_token, req_secret) == ("rt", "rts")
    assert request_route.calls.last.request.headers["Authorization"].startswith(
        "OAuth "
    )

    token, secret = client.complete_oauth(req_token, req_secret, "verif")
    assert (token, secret) == ("at", "ats")
    access_header = access_route.calls.last.request.headers["Authorization"]
    assert 'oauth_token="rt"' in access_header
    assert 'oauth_verifier="verif"' in access_header
