# Developer Guide

This guide covers everything you need to set up a development environment, run tests, and contribute to VinylKit.

---

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — fast Python package and project manager

Install `uv` if you haven't already:

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Development Setup

### Clone and Install Dependencies

```bash
git clone https://github.com/alaninspace/vinyl-man.git
cd vinyl-man
uv sync          # installs all dependencies, including the dev group
```

### Running the CLI in Dev Mode

Use `uv run` to execute the CLI directly from source without installing:

```bash
uv run vinylkit [COMMAND]
```

### Installing as a Global Tool

```bash
uv tool install . --force
```

After installing globally, the `vinylkit` command is available everywhere in your terminal.

### Rebuilding After Changes

```bash
uv tool install . --force --no-cache
```

> [!NOTE]
> Your configuration file persists across reinstalls. It lives in a platform-specific location managed by `platformdirs` (e.g. `%LOCALAPPDATA%\vinylkit\config.toml` on Windows), not inside the repo.

---

## Project Structure

```text
src/
└── vinylkit/
    ├── cli.py          # Click commands, helpers, and main entry point
    ├── config.py       # TOML config loading and saving (platformdirs)
    ├── discogs.py      # Discogs API client, OAuth, and response caching
    ├── exceptions.py   # Custom exception hierarchy
    ├── models.py       # Frozen dataclasses (slots) and enums
    ├── naming.py       # Path generation, template rendering, file moves
    ├── tagging.py      # Mutagen-based MP3 (ID3v2) and FLAC tagging
    └── utils.py        # Backup helpers and filename sanitization
tests/
    ├── test_cli.py               # CLI command tests (CliRunner)
    ├── test_discogs.py           # Discogs API client tests (respx)
    ├── test_naming.py            # Naming and path generation tests
    ├── test_tagging.py           # Tagging logic tests
    ├── test_tagging_modes.py     # Tag mode (replace/merge) tests
    ├── test_expanded_metadata.py # Expanded metadata field tests
    ├── test_auth_logic.py        # Authentication priority chain tests
    └── test_examples_coverage.py # Ensures every doc example has a test
docs/
    ├── quickstart.md       # Setup and basic workflow
    ├── user-guide.md       # In-depth command and feature reference
    ├── examples.md         # Real-world command combinations
    ├── configuration.md    # Full list of all settings
    ├── auth.md             # Discogs authentication guide
    ├── data-model.md       # Data model reference
    ├── spec.md             # Feature specification
    └── developer-guide.md  # This file
```

---

## Architecture Overview

### Synchronous CLI

VinylKit is a synchronous CLI built on **Click** with **httpx** `SyncClient` for API calls. There is no async code — this keeps the CLI simple and debuggable.

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `cli.py` | Click command definitions, shared helpers (`_collect_audio_files`, `_display_relative`, `_plan_supplementary_moves`), `_CONFIG_CONVERTERS` dict |
| `config.py` | TOML config loading/saving via `tomllib` / `tomli-w`, path resolution via `platformdirs` |
| `discogs.py` | Discogs API client, OAuth flow, response caching |
| `models.py` | Frozen dataclasses with `slots=True` (e.g. `DiscogsRelease`, `AppConfig`, `AudioFile`) and enums (`TagMode`, `AuthMode`, etc.) |
| `naming.py` | Filename template rendering, path generation, and safe file moves |
| `tagging.py` | Mutagen-based tagging for MP3 (ID3v2) and FLAC (Vorbis comments), artwork embedding |
| `utils.py` | Backup file creation and filename sanitization |
| `exceptions.py` | Custom exception hierarchy rooted at `VinylkitError` |

### Data Flow

```
CLI command (click)
  → DiscogsClient (httpx)
    → DiscogsRelease model (frozen dataclass)
      → tagging.py (write tags to audio files)
      → naming.py (generate paths, move/rename files)
```

### Key Conventions

- **`from __future__ import annotations`** in every file
- **Frozen dataclasses with `slots=True`** for all models — immutable and memory-efficient
- **Custom exceptions** for user-facing errors — never leak raw library exceptions to the CLI
- **`VinylkitError`** hierarchy: `ConfigError`, `AuthError`, `DiscogsAPIError`, `TaggingError`, `FileOperationError`, `ValidationError`

---

## Running Tests

VinylKit uses **pytest** as its test runner.

```bash
# Run all tests
uv run pytest

# Verbose output
uv run pytest -v

# With coverage
uv run pytest --cov

# Run a single test file
uv run pytest tests/test_cli.py

# Run a specific test by name
uv run pytest -k "test_name"
```

### Testing Stack

| Tool | Purpose |
|---|---|
| `pytest` | Test runner |
| `pytest-mock` | Mocking via `mocker` fixture |
| `pytest-cov` | Coverage reporting |
| `click.testing.CliRunner` | CLI invocation testing |
| `respx` | HTTP request mocking for Discogs API tests |

### Test Conventions

- **No shared `conftest.py`** — fixtures are defined per test file.
- **Docs/examples parity** — every example in [`docs/examples.md`](examples.md) must have a corresponding test in `tests/test_examples_coverage.py`. If you add an example, add a test.

---

## Linting, Formatting & Type Checking

### Ruff (Lint + Format)

```bash
# Check for linting errors
uv run ruff check .

# Auto-fix what can be fixed
uv run ruff check . --fix

# Format code (88-char line length)
uv run ruff format .
```

**Enabled rule sets:** `E`, `F`, `W` (pycodestyle + pyflakes), `I` (isort), `N` (pep8-naming), `UP` (pyupgrade), `B` (bugbear), `A` (builtins), `SIM` (simplify), `TCH` (type-checking), `RUF` (ruff-specific), `PT` (pytest-style), `RET` (return), `ARG` (unused-arguments), `PTH` (use-pathlib), `PERF` (perflint), `FURB` (refurb).

### mypy (Type Checking)

```bash
uv run mypy src/
```

mypy runs in **strict mode**. All new code must be fully type-hinted.

**Known overrides in `pyproject.toml`:**

| Override | Reason |
|---|---|
| `mutagen.*`, `authlib.*` — `ignore_missing_imports = true` | These libraries do not ship type stubs |
| `vinylkit.tagging` — `disallow_untyped_calls = false` | Mutagen's API is untyped |
| `vinylkit.tagging` — `disable_error_code = ["attr-defined"]` | Mutagen uses dynamic attribute access |

---

## Adding a New CLI Command

1. **Define the command** in `cli.py` using Click decorators:

```python
@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.pass_obj
def my_command(config: AppConfig, path: str) -> None:
    """Short description for --help."""
    ...
```

2. **Use `@click.pass_obj`** to access the `AppConfig` instance.
3. **Raise custom exceptions** from `vinylkit.exceptions` for user-facing errors — the `main()` wrapper catches `VinylkitError` and prints it cleanly.
4. **Add tests** using `CliRunner` and `isolated_filesystem`:

```python
from click.testing import CliRunner
from vinylkit.cli import cli

def test_my_command() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["my-command", "."])
        assert result.exit_code == 0
```

---

## Adding a New Config Option

1. **Add a field** to `AppConfig` in `models.py`:

```python
@dataclass(slots=True, frozen=True)
class AppConfig:
    ...
    my_option: str = "default_value"
```

2. **Update `load_config()`** in `config.py` to read the new field from TOML.
3. **Update `save_config()`** in `config.py` to write it back.
4. **Add a converter entry** in `_CONFIG_CONVERTERS` in `cli.py` so `config set` works:

```python
_CONFIG_CONVERTERS: dict[str, Callable[[str], Any]] = {
    ...
    "my_option": str,
}
```

5. **Add to `config show` output** in `cli.py`.
6. **Update [`docs/configuration.md`](configuration.md)** with the new option.

---

## Documentation Rules

- Any **new feature** must include updates to the relevant docs (README, user-guide, etc.).
- Any **new example** added to [`docs/examples.md`](examples.md) must have a corresponding test case in `tests/test_examples_coverage.py`.

---

## Code Conventions

| Convention | Detail |
|---|---|
| Future annotations | `from __future__ import annotations` in every file |
| Type hints | All functions fully type-hinted; must pass `mypy --strict` |
| Error handling | Custom exceptions from `vinylkit.exceptions`; never leak raw library exceptions |
| Safety | Destructive operations (rename, move) default to dry-run or require confirmation |
| Line length | 88 characters |
| Style | PEP 8 via ruff |
