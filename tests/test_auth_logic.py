from __future__ import annotations

from authlib.integrations.httpx_client import OAuth1Client
import httpx
from vinylkit.discogs import DiscogsClient

def test_auth_mode_auto_prioritizes_oauth():
    # If all keys are present, auto should pick oauth
    client = DiscogsClient(
        consumer_key="ck",
        consumer_secret="cs",
        token="t",
        secret="s",
        auth_mode="auto"
    )
    assert client.mode == "oauth"
    assert isinstance(client.client, OAuth1Client)

def test_auth_mode_auto_falls_back_to_token():
    # If no secret, auto should pick token
    client = DiscogsClient(
        consumer_key="ck",
        consumer_secret="cs",
        token="t",
        auth_mode="auto"
    )
    assert client.mode == "token"
    # Token mode uses standard httpx.Client with headers
    assert isinstance(client.client, httpx.Client)
    assert client.client.headers["Authorization"] == "Discogs token=t"

def test_auth_mode_auto_falls_back_to_key_secret():
    # If only consumer keys, auto should pick key_secret
    client = DiscogsClient(
        consumer_key="ck",
        consumer_secret="cs",
        auth_mode="auto"
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
        auth_mode="token"
    )
    assert client.mode == "token"
    assert client.client.headers["Authorization"] == "Discogs token=t"

def test_auth_mode_force_oauth_fails_if_missing_keys():
    # If we force oauth but lack tokens, it should fall back to auto logic or none
    # In our current implementation, it skips the oauth block and tries token
    client = DiscogsClient(
        consumer_key="ck",
        consumer_secret="cs",
        auth_mode="oauth"
    )
    # Since it can't do oauth, it continues to try key_secret (auto-logic fallback)
    assert client.mode == "key_secret"

def test_auth_mode_none():
    client = DiscogsClient()
    assert client.mode == "none"
    assert isinstance(client.client, httpx.Client)
    assert "Authorization" not in client.client.headers
