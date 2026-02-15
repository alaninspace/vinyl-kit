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
git clone https://github.com/alaninspace/vinyl-kit.git
cd vinyl-kit
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
> Your configuration file persists across reinstalls. It lives in a platform-specific location managed by `platformdirs` (e.g. `%LOCALAPPDATA%\vinylkit\config.toml` on Windows, `~/Library/Application Support/vinylkit/config.toml` on macOS, `~/.config/vinylkit/config.toml` on Linux), not inside the repo.

---

## Project Structure

```text
src/
└── vinylkit/
    ├── __init__.py     # Package marker
    ├── __main__.py     # Entry point for `python -m vinylkit`
    ├── cli.py          # Root Click group, logging setup, main() entry point
    ├── commands/
    │   ├── __init__.py     # Package marker
    │   ├── _helpers.py     # Shared helpers, constants, and re-exported deps
    │   ├── tag.py          # scan, tag, rename commands
    │   ├── migrate.py      # migrate command
    │   ├── auth.py         # auth group: login, identity
    │   ├── collection.py   # collection group: download
    │   ├── config_cmd.py   # config group: show, set + _CONFIG_CONVERTERS
    │   └── cache.py        # cache group: list, clear
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
    ├── test_cache.py              # Cache list and clear command tests
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

VinylKit is a synchronous CLI built on **Click** with **httpx** `Client` for API calls. There is no async code — this keeps the CLI simple and debuggable.

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `cli.py` | Root Click group, `initialise_logging()`, `main()` entry point. Registers commands from `commands/` subpackage |
| `commands/_helpers.py` | Shared helpers (`collect_audio_files`, `display_relative`, `plan_supplementary_moves`, `check_collisions`, `download_artwork`, `save_release_files`), re-exported deps for single-point mocking |
| `commands/tag.py` | `scan`, `tag`, `rename` commands |
| `commands/migrate.py` | `migrate` command, `_extract_id` helper |
| `commands/auth.py` | `auth` group with `login`, `identity` |
| `commands/collection.py` | `collection` group with `download` |
| `commands/config_cmd.py` | `config` group with `show`, `set`, `_CONFIG_CONVERTERS` dict |
| `commands/cache.py` | `cache` group with `list`, `clear`, `_format_age` helper |
| `config.py` | TOML config loading/saving via `tomllib` / `tomli-w`, path resolution via `platformdirs` |
| `discogs.py` | Discogs API client, OAuth flow, response caching, rate limit header tracking and dynamic throttling |
| `models.py` | Frozen dataclasses with `slots=True` (e.g. `DiscogsRelease`, `AppConfig`, `AudioFile`) and enums (`TagMode`, `AuthMode`, etc.). Exception: `RateLimitInfo` is intentionally mutable |
| `naming.py` | Filename template rendering, path generation, and safe file moves (cross-drive via `shutil.move`) |
| `tagging.py` | Mutagen-based tagging for MP3 (ID3v2) and FLAC (Vorbis comments), artwork embedding/saving, folder scanning (`scan_folder`), tag clearing (`clear_audio_tags`), track/disc calculation (`calculate_track_and_disc`), release info writing (`write_release_info`) |
| `utils.py` | Backup file creation, filename sanitization, and path resolution (`ensure_absolute`) |
| `exceptions.py` | Custom exception hierarchy rooted at `VinylkitError` |

### Data Flow

```
CLI command (click, ctx.obj=AppConfig)
  → DiscogsClient (httpx)
    → DiscogsRelease model (frozen dataclass)
      → tagging.py (write tags to audio files)
      → naming.py (generate paths, move/rename files)
```

### Key Conventions

- **`from __future__ import annotations`** in every file
- **Frozen dataclasses with `slots=True`** for most models — immutable and memory-efficient. Exception: `RateLimitInfo` is intentionally mutable (updated in-place on every API response)
- **Custom exceptions** for user-facing errors — never leak raw library exceptions to the CLI
- **`VinylkitError`** hierarchy: `ConfigError`, `AuthError`, `DiscogsAPIError`, `TaggingError`, `FileOperationError`, `ValidationError`
- **Loguru logging**: Use `from loguru import logger` — no `logging.getLogger(__name__)`. The global `logger` instance routes to both console and file sinks configured in `initialise_logging()`. Stdlib loggers (httpx, authlib) are bridged through an `_InterceptHandler`
- **Two-phase rename**: The `tag` command's post-tagging rename uses two phases — (1) rename files in-place within the source folder so they always have correct names, then (2) move to `library_root`. If phase 2 fails (e.g. permissions), files are still tagged and properly named in the source folder
- **Cross-drive moves**: `move_file` uses `shutil.move` (not `Path.replace`) so that moves between different drives/filesystems work correctly (copy + delete fallback)
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
- **Autouse fixtures** — `_suppress_loguru_file_sink` (session-scoped) prevents loguru file sinks during tests, `_isolate_cache_dir` redirects the cache directory to `tmp_path` for every test, and a `caplog` bridge fixture routes loguru output to pytest's log capture.
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

**Type stubs:**

| Library | Source |
|---|---|
| `mutagen` | Local stubs in `stubs/mutagen/` (no PyPI package exists) |
| `authlib` | `types-authlib` dev dependency |

---

## Adding a New CLI Command

1. **Create a command** in the appropriate `commands/` module (or a new module). Use `@click.command()` (not `@cli.command()`) and register it in `cli.py` via `cli.add_command(my_command)`:

```python
# commands/my_module.py
@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.pass_obj
def my_command(config: AppConfig, path: str) -> None:
    """Short description for --help."""
    ...
```

```python
# cli.py
from vinylkit.commands.my_module import my_command
cli.add_command(my_command)
```

2. **Use `@click.pass_obj`** to access the `AppConfig` instance.
3. **Access mockable deps through `_helpers`** (e.g. `_helpers.tag_audio_file`) so tests can patch `vinylkit.commands._helpers.X` in one place.
4. **Raise custom exceptions** from `vinylkit.exceptions` for user-facing errors — the `main()` wrapper catches `VinylkitError` and prints it cleanly.
5. **Add tests** using the shared `runner` fixture from `conftest.py`:

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
4. **Add a converter entry** in `_CONFIG_CONVERTERS` in `commands/config_cmd.py` so `config set` works:

```python
_CONFIG_CONVERTERS: dict[str, Callable[[str], Any]] = {
    ...
    "my_option": str,
}
```

5. **Add to `config show` output** in `commands/config_cmd.py`.
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
