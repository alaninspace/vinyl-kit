# Developer Guide

This guide covers everything you need to set up a development environment, run tests, and contribute to VinylKit.

---

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — fast Python package and project manager

Install `uv` if you haven't already:

**Bash (macOS / Linux):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**PowerShell (Windows):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Development Setup

### Clone and Install Dependencies

```bash
# Bash / PowerShell
git clone https://github.com/alaninspace/vinyl-man.git
cd vinyl-man
uv sync          # installs all dependencies, including the dev group
```

### Running the CLI in Dev Mode

Use `uv run` to execute the CLI directly from source without installing:

```bash
# Bash / PowerShell
uv run vinylkit [COMMAND]
```

### Installing as a Global Tool

```bash
# Bash / PowerShell
uv tool install . --force
```

After installing globally, the `vinylkit` command is available everywhere in your terminal.

### Rebuilding After Changes

```bash
# Bash / PowerShell
uv tool install . --force --no-cache
```

> [!NOTE]
> Your configuration file persists across reinstalls. It lives in a platform-specific location managed by `platformdirs` (e.g. `%LOCALAPPDATA%\vinylkit\config.toml` on Windows, `~/.config/vinylkit/config.toml` on macOS/Linux), not inside the repo.

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
    ├── conftest.py                # Shared fixtures (runner, mock_discogs, mp3_file, flac_file)
    ├── test_auth_logic.py         # Authentication priority chain tests
    ├── test_cli.py                # Core CLI interaction tests (CliRunner)
    ├── test_cli_commands.py       # rename, scan, auth, config command tests
    ├── test_collisions.py         # File collision detection and overwrite tests
    ├── test_config_roundtrip.py   # Config set → show round-trip verification
    ├── test_discogs.py            # Discogs API client tests (respx)
    ├── test_edge_cases.py         # Unicode, empty tracklist, missing fields
    ├── test_examples_coverage.py  # Ensures every doc example has a test
    ├── test_expanded_metadata.py  # Expanded metadata field tests
    ├── test_logging.py            # Loguru initialisation and config round-trip tests
    ├── test_migrate.py            # Library migration command tests
    ├── test_naming.py             # Naming and path generation tests
    ├── test_tagging.py            # Tagging logic and scan tests
    ├── test_tagging_integration.py # Real MP3/FLAC tag round-trip tests
    ├── test_tagging_modes.py      # Tag mode (replace/merge) behavior tests
    └── test_utils.py              # backup_file, sanitize_filename, ensure_absolute
docs/
    ├── quickstart.md       # Setup and basic workflow
    ├── user-guide.md       # In-depth command and feature reference
    ├── examples.md         # Real-world command combinations
    ├── configuration.md    # Full list of all settings
    ├── tag-mapping.md      # Authoritative tag mapping reference (canonical names, MP3/FLAC keys, sources)
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
| `discogs.py` | Discogs API client, OAuth flow, response caching, rate limit header tracking and dynamic throttling |
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
- **Loguru logging**: Use `from loguru import logger` — no `logging.getLogger(__name__)`. The global `logger` instance routes to both console and file sinks configured in `initialise_logging()`. Stdlib loggers (httpx, authlib) are bridged through an `_InterceptHandler`
- **Logging convention**: Per-file operations in modules (`tagging.py`, `naming.py`) use `logger.debug()` so they only appear in the log file. Command-level summaries and release separators in `cli.py` use `logger.info()`. HTTP request tracing in `discogs.py` uses `logger.debug()`. Third-party HTTP loggers (httpx, httpcore) are suppressed to WARNING

---

## Running Tests

VinylKit uses **pytest** as its test runner.

```bash
# Bash / PowerShell

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

- **Shared `conftest.py`** — common fixtures live in `tests/conftest.py`:
  - `runner` — `CliRunner` with config isolated via `VINYLKIT_CONFIG` env var (prevents reading/writing real user config).
  - `mock_discogs` — patches `get_client`, `tag_audio_file`, `clear_audio_tags`, `write_release_info`, and `save_artwork`. Does **not** mock `move_file`/`move_directory` — tests that need file movement suppressed should patch those locally.
  - `mp3_file` / `flac_file` — minimal valid audio files for real tagging round-trip tests.
  - `create_mock_release()` — helper function (not a fixture) for building `DiscogsRelease` objects with sensible defaults.
- **Docs/examples parity** — every example in [`docs/examples.md`](examples.md) must have a corresponding test in `tests/test_examples_coverage.py`. If you add an example, add a test.

---

## Linting, Formatting & Type Checking

### Ruff (Lint + Format)

```bash
# Bash / PowerShell

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
# Bash / PowerShell
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
4. **Add tests** using the shared `runner` fixture from `conftest.py`:

```python
from vinylkit.cli import cli

def test_my_command(runner, tmp_path) -> None:
    result = runner.invoke(cli, ["my-command", str(tmp_path)])
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
