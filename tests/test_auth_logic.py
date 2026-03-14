from __future__ import annotations

import httpx
from authlib.integrations.httpx_client import OAuth1Client

from vinylkit.discogs import DiscogsClient
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
    assert isinstance(client.client, OAuth1Client)


def test_auth_mode_auto_falls_back_to_token():
    # If no secret, auto should pick token
    client = DiscogsClient(
        consumer_key="ck", consumer_secret="cs", token="t", auth_mode=AuthMode.AUTO
    )
    assert client.mode == "token"
    # Token mode uses standard httpx.Client with headers
    assert isinstance(client.client, httpx.Client)
    assert client.client.headers["Authorization"] == "Discogs token=t"


def test_auth_mode_auto_falls_back_to_key_secret():
    # If only consumer keys, auto should pick key_secret
    client = DiscogsClient(
        consumer_key="ck", consumer_secret="cs", auth_mode=AuthMode.AUTO
    )
    assert client.mode == "key_secret"
    # key_secret uses OAuth1Client (needed for login flow)
    assert isinstance(client.client, OAuth1Client)


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
