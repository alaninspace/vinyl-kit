"""Shared console and output helpers for the CLI.

Everything the CLI prints goes through here so messages, tables and
key/value blocks look the same across commands.

Layout rule: no line is wider than its content. Nothing is padded out to
a right-hand border, so when a terminal window is made narrower after
the output is printed, lines re-wrap as plain text instead of leaving
border characters and padding on rows of their own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rich.console import RenderableType

# Tables and key/value blocks never render wider than this, however wide
# the terminal is.
MAX_WIDTH = 100

# Below this width a key/value block puts each value under its key.
STACK_BELOW = 64

# Width of the key column in a key/value block (fits the longest setting
# name plus its indent).
KEY_WIDTH = 30

# Shared Rich console
console = Console()


def content_width() -> int:
    """Return the width to lay out tables and key/value blocks in."""
    return min(console.width, MAX_WIDTH)


def glyph(fancy: str, plain: str) -> str:
    """Return *fancy*, or *plain* when the output encoding isn't UTF-8.

    Piped or redirected output on Windows is often cp1252, which can't
    encode the status glyphs.
    """
    return plain if console.options.ascii_only else fancy


def heading(title: str, detail: str = "") -> None:
    """Print a bold heading with an optional dim detail after it."""
    text = Text(title, style="bold")
    if detail:
        text.append(f"  {detail}", style="dim")
    console.print(text, highlight=False, soft_wrap=True)


def success(message: str) -> None:
    """Print a completed-action line. *message* may contain Rich markup."""
    console.print(
        f"[green]{glyph('✓', 'ok:')}[/green] {message}",
        highlight=False,
        soft_wrap=True,
    )


def warning(message: str) -> None:
    """Print a warning line. *message* may contain Rich markup."""
    console.print(f"[yellow]![/yellow] {message}", highlight=False, soft_wrap=True)


def error(message: str, hint: str = "") -> None:
    """Print an error line, with an optional dim next-step *hint* under it."""
    console.print(
        f"[bold red]{glyph('✗', 'error:')}[/bold red] {message}",
        highlight=False,
        soft_wrap=True,
    )
    if hint:
        detail(hint)


def detail(message: str) -> None:
    """Print a dim, indented supporting line under a status line."""
    console.print(f"  [dim]{message}[/dim]", highlight=False, soft_wrap=True)


def make_table() -> Table:
    """Return a table with a header rule and no outer or column borders."""
    return Table(
        box=box.SIMPLE_HEAD,
        show_edge=False,
        pad_edge=False,
        header_style="dim",
        padding=(0, 2, 0, 0),
    )


def print_trimmed(renderable: RenderableType) -> None:
    """Print *renderable* with no padding to the right of each line.

    Rich pads table rows to the table width. Stripping that keeps every
    line as short as its content.
    """
    options = console.options.update_width(content_width())
    for line in console.render_lines(renderable, options, pad=False):
        text = Text()
        for segment in line:
            if not segment.control:
                text.append(segment.text, segment.style)
        text.rstrip()
        console.print(text, highlight=False, soft_wrap=True)


def print_table(table: Table) -> None:
    """Print a table made with :func:`make_table`."""
    print_trimmed(table)


def print_section(title: str, rows: Sequence[tuple[str, RenderableType]]) -> None:
    """Print a key/value block, under *title* unless it is empty.

    Values sit beside their keys, or under them when the terminal is
    narrower than :data:`STACK_BELOW`.
    """
    if title:
        console.print(Text(title, style="bold magenta"), highlight=False)
    if content_width() < STACK_BELOW:
        for key, value in rows:
            console.print(Text(f"  {key}", style="cyan"), highlight=False)
            indented = Table.grid(padding=(0, 2))
            indented.add_column(width=2)
            indented.add_column(overflow="fold")
            indented.add_row("", value)
            print_trimmed(indented)
        return
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="cyan", no_wrap=True, min_width=KEY_WIDTH)
    grid.add_column(overflow="fold")
    for key, value in rows:
        grid.add_row(f"  {key}", value)
    print_trimmed(grid)
