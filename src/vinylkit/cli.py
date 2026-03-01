"""VinylKit CLI entry point.

Defines the root Click group, logging setup, and ``main()`` entry
point.  Individual commands live in :mod:`vinylkit.commands`.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
from loguru import logger
from platformdirs import user_log_dir

from vinylkit import __version__
from vinylkit.commands._helpers import console
from vinylkit.commands.auth import auth
from vinylkit.commands.cache import cache
from vinylkit.commands.collection import collection
from vinylkit.commands.config_cmd import config_group
from vinylkit.commands.migrate import migrate
from vinylkit.commands.tag import rename, scan, tag
from vinylkit.config import load_config
from vinylkit.exceptions import VinylkitError

if TYPE_CHECKING:
    from types import FrameType

    from vinylkit.models import AppConfig


class _InterceptHandler(logging.Handler):
    """Route stdlib log records (httpx, authlib) through loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: FrameType | None
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def initialise_logging(config: AppConfig) -> None:
    """Configure loguru sinks based on user settings."""
    logger.remove()

    # Console sink at user-configured level
    logger.add(
        sys.stderr,
        level=config.log_level,
        format="<level>{level: <8}</level> | {message}",
        colorize=True,
    )

    # File sink (if enabled)
    if config.log_to_file:
        log_path = config.log_file or (
            Path(user_log_dir("vinylkit", ensure_exists=True)) / "vinylkit.log"
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_path,
            level="DEBUG",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8}"
                " | {name}:{function}:{line} | {message}"
            ),
            rotation=config.log_rotation,
            retention=config.log_retention,
            encoding="utf-8",
        )

    # Bridge stdlib logging (httpx, authlib) through loguru
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    # Suppress httpcore and httpx noise
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """VinylKit: Manage your digitized vinyl collection with Discogs metadata."""
    ctx.obj = load_config()
    initialise_logging(ctx.obj)


# Register command modules
cli.add_command(scan)
cli.add_command(tag)
cli.add_command(rename)
cli.add_command(migrate)
cli.add_command(auth)
cli.add_command(collection)
cli.add_command(config_group, "config")
cli.add_command(cache)


def main() -> None:
    try:
        cli(obj=None)
    except VinylkitError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        logger.exception("An unexpected error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
