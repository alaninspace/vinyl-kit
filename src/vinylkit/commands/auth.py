"""auth group: login, identity commands."""

from __future__ import annotations

import rich_click as click

from vinylkit.commands import _helpers
from vinylkit.config import save_config
from vinylkit.exceptions import VinylkitError
from vinylkit.models import AppConfig


@click.group()
def auth() -> None:
    """Authenticate with Discogs (login, identity).

    VinylKit supports OAuth 1.0a and personal access tokens.
    Use 'auth login' to start the OAuth flow, or set a personal
    token via 'config set discogs_token <TOKEN>'.
    """


_LOGIN_EPILOG = (
    "[bold]Examples:[/bold]\n\n  vinylkit auth login\n\n  vinylkit auth identity"
)


@auth.command(epilog=_LOGIN_EPILOG)
@click.pass_obj
def login(config: AppConfig) -> None:
    """Authenticate with Discogs using OAuth 1.0a."""
    if not config.consumer_key or config.consumer_key == _helpers.DEFAULT_CONSUMER_KEY:
        _helpers.console.print(
            "[bold red]Error:[/bold red] You must set your own"
            " [bold]consumer_key[/bold] and"
            " [bold]consumer_secret[/bold]"
            " before logging in."
        )
        _helpers.console.print(
            "See the [bold]Authentication Guide (auth.md)[/bold] for instructions."
        )
        return

    client = _helpers.get_client(config)

    try:
        url, req_token, req_token_secret = client.get_authorize_url()
        _helpers.console.print(
            "\n1. Please visit this URL to authorize"
            f" VinylKit:\n[link={url}]{url}[/link]\n"
        )
        verifier = click.prompt("2. Enter the verifier code provided by Discogs")

        access_token, access_token_secret = client.complete_oauth(
            req_token, req_token_secret, verifier
        )

        # Preserve ALL existing fields, only overwrite the two
        # tokens produced by the OAuth flow.
        updated = {
            field: getattr(config, field) for field in AppConfig.__dataclass_fields__
        }
        updated["discogs_token"] = access_token
        updated["discogs_secret"] = access_token_secret
        new_config = AppConfig(**updated)
        save_config(new_config)
        _helpers.console.print(
            "[bold green]Success![/bold green] You are now authenticated with Discogs."
        )

        client = _helpers.get_client(new_config)
        identity_data = client.get_identity()
        _helpers.console.print(
            f"Authenticated as: [bold]{identity_data.get('username')}[/bold]"
        )
    except VinylkitError as e:
        _helpers.console.print(f"[bold red]Authentication failed:[/bold red] {e}")


@auth.command()
@click.pass_obj
def identity(config: AppConfig) -> None:
    """Display the authenticated Discogs user."""
    client = _helpers.get_client(config)
    try:
        identity_data = client.get_identity()
        _helpers.console.print(
            f"Authenticated as: [bold]{identity_data.get('username')}[/bold]"
        )
        name = identity_data.get("name") or "Not set"
        _helpers.console.print(f"Name: {name}")
        _helpers.console.print(f"URL: {identity_data.get('resource_url')}")
    except VinylkitError as e:
        _helpers.console.print(f"[bold red]Failed to get identity:[/bold red] {e}")
