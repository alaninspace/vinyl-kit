# GEMINI.md

This document provides high-performance system instructions for the Gemini CLI when working on the `vinyl-kit` repository. Follow these directives strictly.

<system_identity>
**Project Summary:**
VinylKit is a cross-platform CLI application for managing and standardising digitised vinyl record audio files using Discogs metadata.

**Tech Stack:**

- **Language:** Python 3.12+
- **Package Manager:** `uv`
- **CLI Framework:** `click` (via `rich-click`)
- **HTTP Client:** `httpx` (sync)
- **Tagging Engine:** `mutagen` (with local type stubs)
- **Logging:** `loguru`
</system_identity>

<agent_execution_mandate>

- **Autonomy:** You are explicitly authorised to run the test suite, `ruff`, and `mypy` autonomously via shell commands after modifying files. Do not ask the user for permission to validate your code.
- **Self-Correction:** If your checks fail, autonomously analyse the output and apply fixes before reporting back to the user.
</agent_execution_mandate>

## Core Commands

```bash
uv run pytest                        # Run all tests
uv run pytest tests/test_name.py     # Run specific test file
uv run ruff check .                  # Lint codebase
uv run ruff check . --fix            # Auto-fix linting issues
uv run ruff format .                 # Format codebase
uv run mypy src/                     # Type check (must target src/, not .)
uv run vinylkit [COMMAND]            # Run the CLI locally
```

<critical_directives>

### 1. Zero-Warning Policy

All `ruff` and `mypy` checks MUST pass with **zero warnings and zero errors**. No exceptions are permitted.

- Run `uv run mypy src/` for type checking.
- Do not introduce new warnings or leave existing ones unresolved.
- Two `# type: ignore` comments exist in `discogs.py` as workarounds for authlib stub bugs; do not remove them unless the upstream bug is resolved.

### 2. Code Style & Syntax

- **Future Annotations:** Every Python file MUST begin with `from __future__ import annotations`.
- **Line Length:** Strictly adhere to an 88-character maximum line length. Use implicit string concatenation for long strings.
- **Exception Chaining:** Always use `raise ... from err` (or `from None`) to chain exceptions (Ruff B904). Never use a bare `raise` inside an `except` block.
- **Path Manipulation:** Use `pathlib.Path` (e.g., `Path(...) / "segment"`) instead of `os.path.join()` (Ruff PTH118).
- **Unused Variables:** Prefix unused variables with an underscore `_` or omit them entirely.
- **Type Narrowing:** Use distinct variable names to avoid `mypy` redefinition conflicts when variables are reassigned in different scopes.
- **Imports:** Place type-only imports inside `TYPE_CHECKING` blocks (Ruff TC002/TC003). Imports required at runtime for default values (e.g., `Path` in dataclass fields) must remain at the top level.

### 3. Type Safety

- **Domain Enums:** Use `StrEnum` for domain logic (`TagMode`, `AuthMode`, `ImageHandling`, `TrackNumbering`, `DiscMapping`). Always use enum members for comparisons and assignments (e.g., `TagMode.REPLACE`, never `"replace"`).
- **Canonical Tags:** Use `TagName` members defined in `tagging.py` for all tag-writing code.
- **Function Signatures:** All functions must be fully type-hinted and pass `mypy --strict`.
</critical_directives>

<anti_patterns>
**DO NOT DO THE FOLLOWING:**

- DO NOT use bare strings for domain values (e.g., `"replace"`); use `TagMode.REPLACE`.
- DO NOT use bare strings for tag names; use `TagName` members.
- DO NOT write test data directly to the host OS; strictly use `pytest`'s `tmp_path`.
- DO NOT use standard `logging`; strictly use `loguru`.
- DO NOT suppress exceptions or use blanket `# type: ignore` directives to bypass the zero-warning policy.
</anti_patterns>

## Architectural Patterns

### 1. Data Flow

```text
CLI command (click, ctx.obj=AppConfig)
  -> DiscogsClient (httpx sync)
    -> DiscogsRelease (frozen dataclass)
      -> tagging.py (writes tags via mutagen)
      -> naming.py (generates paths, executes file moves/renames)
```

### 2. Module Responsibilities

- **`cli.py`**: Root `click` group, logger initialisation, and `main()` entry point.
- **`commands/`**: Contains CLI groups (`tag.py`, `migrate.py`, `auth.py`, `collection.py`, `config_cmd.py`, `cache.py`) and `_helpers.py` for shared logic.
- **`config.py`**: Handles TOML load/save operations, manually mapping to the `AppConfig` frozen dataclass. The `_CONFIG_CONVERTERS` dict maps config keys to converter functions.
- **`discogs.py`**: API client handling authorisation, response caching, and rate limiting (with exponential backoff).
- **`models.py`**: Centralises frozen dataclasses and enums. All models are strictly `@dataclass(slots=True, frozen=True)` (except `RateLimitInfo`).
- **`naming.py`**: Generates path templates and safely orchestrates file and directory moves. Destructive operations (rename, move, delete) default to dry-run or require confirmation.
- **`tagging.py`**: Manages MP3 (ID3v2) and FLAC (Vorbis) tagging via `mutagen`, embeds/saves artwork, and executes vinyl position logic.
- **`utils.py`**: Provides file backup and filename sanitisation (NFC normalisation, illegal character removal, UTF-8 truncation).
- **`exceptions.py`**: Custom exception hierarchy. Catch specific types (e.g., `OSError`, `DiscogsAPIError`), never bare `Exception`.

### 3. Core Mechanisms

- **Vinyl Position Logic (`calculate_track_and_disc`):** Returns track and disc numbers as strings based on `TrackNumbering` (`NUMERIC`, `ORIGINAL`, `PER_SIDE`) and `DiscMapping` (`SINGLE`, `PER_SIDE`, `PHYSICAL`, `ORIGINAL`).
- **Artwork Handling:** The constant `FRONT_COVER_TYPE = 3` is used for ID3 APIC and FLAC Picture types. Primary images are saved as `config.artwork_filename` (e.g., `folder.jpg`), and secondary images as `primary_01.jpg`, `secondary_01.jpg`, etc.
- **Authorisation Chain:** Evaluated in order: `oauth` (full OAuth 1.0a) -> `token` (personal access token) -> `key_secret` (consumer key/secret) -> `none` (unauthenticated fallback).

## Testing & QA Protocol

### 1. Fixture & Mocking Requirements

- **Location:** All shared fixtures reside in `tests/conftest.py` (e.g., `runner`, `mock_discogs`, `mp3_file`, `flac_file`, `create_mock_release`, `caplog`).
- **API Mocking:** External API calls MUST be mocked. Use `respx` for HTTP-level mocking in `test_discogs.py`.
- **Function Mocking:** `mock_discogs` patches helpers in `commands/_helpers.py`. Note that `move_file` and `move_directory` are NOT patched by default; tests requiring suppressed file movement must patch these locally.

### 2. Pathing & Data Isolation (CRITICAL)

- **Temporary Directories:** ALL test data, config, logs, and cache files MUST be written to `pytest`'s `tmp_path` fixture or equivalent temporary directories.
- **No Platform Leakage:** Never write test data to real platform directories. The `_isolate_cache_dir` autouse fixture redirects the cache directory for every test. The `_suppress_loguru_file_sink` fixture prevents log file I/O during tests.
- **Audio Files:** Use `_make_mp3_bytes` and `_make_flac_bytes` to generate minimal valid audio files in memory. Do not save test data files on disk permanently.

### 3. Test Organisation

- Place tests in the existing file that matches their logical subject (e.g., `test_tagging.py`, `test_discogs.py`). Do not create ad-hoc files like `test_bugfixes.py`. If no existing file fits, create one named after the module or feature (e.g., `test_<module>.py`).

<definition_of_done>
Before marking any task as complete, you MUST execute this workflow sequentially:

1. **Write & Verify Tests:** Every new behaviour, feature, or bug fix must have an accompanying test case. Run tests to confirm the fix/feature works as expected.
2. **Documentation Sweep:** Update all relevant markdown files in `docs/`:
   - `configuration.md`: Document ALL new settings, flags, and allowed values. This is the authoritative reference.
   - `user-guide.md` & `examples.md`: Add practical examples for new commands or flags.
   - `help output`: Update `epilog` strings and `@click.option(help=...)` inside command source files (e.g., `_TAG_EPILOG` in `tag.py`).
3. **Ensure Example Parity:** Any example added to `docs/examples.md` MUST have a corresponding test in `tests/test_examples_coverage.py`.
4. **Flag Coverage Rule:** Every new CLI flag/option MUST be:
   - Documented in `configuration.md` with an example.
   - Shown in at least one example in `docs/examples.md`.
   - Covered by an automated test in `tests/test_examples_coverage.py`.
5. **Version Bump:** Increment the semantic version in `pyproject.toml` (Patch for bug fixes/docs, Minor for new features, Major for breaking changes).
6. **Final Validation Suite:** Execute the full check suite to guarantee the zero-warning policy:
   `uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy src/`
</definition_of_done>
