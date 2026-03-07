# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

VinylKit is a cross-platform CLI tool for managing digitized vinyl record audio files using Discogs metadata. Python 3.12+, managed with `uv`.

## Commands

```bash
uv run pytest                        # run all tests
uv run pytest tests/test_foo.py      # run one test file
uv run pytest -k "test_name"         # run tests matching pattern
uv run ruff check .                  # lint
uv run ruff check . --fix            # auto-fix lint
uv run ruff format .                 # format
uv run mypy src/                     # type check (must target src/, not .)
uv run vinylkit [COMMAND]            # run the CLI locally
```

## Project Layout

```text
src/vinylkit/
  __init__.py, __main__.py
  cli.py          # Root Click group, logging setup, main() entry point
  commands/
    __init__.py     # Package marker
    _helpers.py     # Shared helpers, constants, re-exported mockable deps
    tag.py          # scan, tag, rename commands
    migrate.py      # migrate command
    auth.py         # auth group: login, identity
    collection.py   # collection group: download
    config_cmd.py   # config group: show, set + _CONFIG_CONVERTERS
    cache.py        # cache group: list, clear
  config.py       # TOML load/save
  discogs.py      # API client, OAuth, caching
  models.py       # Frozen dataclasses & enums
  naming.py       # Filename templates, file/dir moves
  tagging.py      # MP3/FLAC tagging, artwork, track/disc calc
  utils.py        # Backup, filename sanitization
  exceptions.py   # Custom exception hierarchy
stubs/mutagen/    # Local type stubs for mutagen
tests/
  conftest.py                # Shared fixtures
  test_cli.py                # Core CLI integration tests
  test_cli_commands.py       # Command-level tests
  test_examples_coverage.py  # Parity tests for docs/examples.md
  test_tagging.py            # Tag unit tests
  test_tagging_integration.py # Round-trip MP3/FLAC tagging
  test_tagging_modes.py      # TagMode / skip_tags tests
  test_naming.py             # Template & move logic
  test_discogs.py            # API client (uses respx)
  test_config_roundtrip.py   # Config save/load cycle
  test_auth_logic.py         # Auth mode selection
  test_cache.py              # Cache commands
  test_collisions.py         # Rename collision detection
  test_edge_cases.py         # Corner-case coverage
  test_expanded_metadata.py  # Extended Discogs tags
  test_help.py               # Help output and rich-click formatting tests
  test_logging.py            # Logging setup
  test_migrate.py            # Migration command
  test_utils.py              # Utility functions
```

## CLI Commands

| Command | Purpose |
| --- | --- |
| `scan [PATHS]` | Report audio files and their tag status |
| `tag [PATHS]` | Tag audio files using Discogs metadata. Key flags: `--id`, `--search`, `--artist`, `--album`, `--format`, `--merge`, `--auto-move`, `--dry-run`, `--no-artwork`, `--rename/--no-rename`, `--library-root` |
| `rename [PATHS]` | Rename/move files using Discogs metadata. Key flags: `--id`, `--commit` (default is dry-run), `--library-root` |
| `migrate SOURCE DEST` | Bulk migrate a tagged library to a new location. Key flags: `--delete`, `--replace-artwork`, `--replace-tags`, `--id` (filter by Discogs IDs), `--dry-run` |
| `auth login` | Start OAuth 1.0a flow with Discogs |
| `auth identity` | Display the authenticated Discogs user |
| `collection download` | Export your Discogs collection to CSV |
| `config show` | Display current configuration |
| `config set KEY VALUE` | Set a configuration value (keys in `_CONFIG_CONVERTERS`) |
| `cache list` | List cached Discogs releases |
| `cache clear [--id N] [-y]` | Clear cached API responses |

## Zero-Warning Policy

All ruff and mypy checks MUST pass clean — **zero warnings, zero errors**. No exceptions. The full check suite (step 4 in the workflow below) includes `mypy src/`. Do not introduce new warnings or leave existing ones unfixed.

Type stubs: `stubs/mutagen/` provides local stubs (no PyPI package exists). `types-authlib` is a dev dependency. Two `# type: ignore` comments in `discogs.py` work around bugs in the authlib stubs (documented inline).

Common pitfalls to avoid:

- **`raise` inside `except`**: Always use `raise ... from err` (or `from None`) to chain exceptions (B904).
- **Line length**: Keep lines under 88 characters. Split long strings with implicit concatenation.
- **Unused variables**: Prefix with `_` or omit (e.g., `_, disc = calculate_track_and_disc(...)`).
- **`os.path` in tests**: Use `Path(...) / "segment"` instead of `os.path.join()` (PTH118).
- **Type narrowing**: When a variable is assigned in multiple scopes (e.g., two loops), use distinct names to avoid mypy `no-redef` / `assignment` conflicts.
- **Imports**: Move type-only imports into `TYPE_CHECKING` blocks (TC002/TC003). Exception: imports used at runtime in defaults (e.g., `Path` in dataclass fields) must stay top-level.

## Architecture

### Data Flow

```text
CLI command (click, ctx.obj=AppConfig)
  -> DiscogsClient (httpx sync)
    -> DiscogsRelease (frozen dataclass)
      -> tagging.py (write tags via mutagen)
      -> naming.py (generate paths, move/rename files)
```

### Module Responsibilities

| Module | Role |
| --- | --- |
| `cli.py` | Root Click group, `initialise_logging()`, `main()` entry point. Registers commands from `commands/` |
| `commands/_helpers.py` | Shared helpers (`collect_audio_files`, `check_collisions`, etc.), re-exported mockable deps (`tag_audio_file`, `move_file`, etc.) |
| `commands/tag.py` | `scan`, `tag`, `rename` commands |
| `commands/migrate.py` | `migrate` command, `_extract_id` helper |
| `commands/auth.py` | `auth` group with `login`, `identity` |
| `commands/collection.py` | `collection` group with `download` |
| `commands/config_cmd.py` | `config` group with `show`, `set`, `_CONFIG_CONVERTERS` dict |
| `commands/cache.py` | `cache` group with `list`, `clear` |
| `config.py` | TOML load/save. Explicit field-by-field mapping between TOML keys and `AppConfig` |
| `discogs.py` | API client, OAuth auth chain (see below), response caching, rate limiting with exponential backoff |
| `models.py` | Frozen dataclasses (`AppConfig`, `DiscogsRelease`, `TrackInfo`, `ImageInfo`, `AudioFile`) and enums (`TagMode`, `ImageHandling`, `TrackNumbering`, `DiscMapping`, `AuthMode`) |
| `naming.py` | Filename templates, path generation, safe file/directory moves |
| `tagging.py` | MP3 (ID3v2) and FLAC (Vorbis) tagging, artwork embedding/saving, `calculate_track_and_disc()` for vinyl position logic |
| `utils.py` | File backup, filename sanitization (NFC normalization, illegal char removal, UTF-8 truncation) |
| `exceptions.py` | Hierarchy: `VinylkitError` -> `ConfigError`, `AuthError`, `DiscogsAPIError`, `TaggingError`, `FileOperationError`, `ValidationError` |

### Key Patterns

- **Config system**: `load_config()` reads TOML and manually maps to `AppConfig` frozen dataclass. `_CONFIG_CONVERTERS` dict maps config keys to converter functions for `config set`.
- **Error handling**: Custom exceptions for user-facing errors (caught in `main()`). Use `logger.warning` for recoverable issues. Catch specific types (`OSError`, `DiscogsAPIError`), never bare `Exception`.
- **All models are frozen**: `@dataclass(slots=True, frozen=True)`. Use `object.__setattr__` in tests when you need to override fields. Exception: `RateLimitInfo` is intentionally mutable (updated in-place during API calls).
- **`FRONT_COVER_TYPE = 3`**: Constant in `tagging.py` for ID3 APIC and FLAC Picture type.
- **Artwork naming**: Primary image in music folder uses `config.artwork_filename` (e.g., `folder.jpg`). Collected artwork in subdir uses `primary_01.jpg`, `secondary_01.jpg`, `secondary_02.jpg`, etc.

### AppConfig Fields (Key Ones)

The full `AppConfig` dataclass is in `models.py`. Notable fields and defaults:

| Field | Default | Notes |
| --- | --- | --- |
| `library_root` | (required) | Target root for organized files |
| `recordings_root` | `None` | Source root for untagged recordings |
| `naming_pattern` | `"{artist}/{year} - {album}/{track_number} - {title}"` | See template placeholders below |
| `tag_mode` | `TagMode.REPLACE` | `replace` or `merge` |
| `track_numbering` | `TrackNumbering.NUMERIC` | `numeric`, `original`, `per_side` |
| `disc_mapping` | `DiscMapping.PHYSICAL` | `single`, `per_side`, `physical`, `original` |
| `image_handling` | `ImageHandling.BOTH` | `embed`, `save`, `both`, `none` |
| `auth_mode` | `AuthMode.AUTO` | `auto`, `token`, `oauth`, `key_secret`, `none` |
| `skip_tags` | `[]` | List of canonical tag names to skip (see `docs/tag-mapping.md`) |
| `auto_move` | `False` | Move files after tagging without prompting |
| `info_filename` | `"release_info.txt"` | Filename for `write_release_info()` output |

See `docs/configuration.md` for the full list with allowed values.

### Naming Template Placeholders

Used in `naming_pattern`. All values are sanitized via `sanitize_filename()`.

`{artist}`, `{album}`, `{year}`, `{track_number}`, `{title}`, `{label}`, `{catalogue_number}`, `{side}`, `{id}` / `{discogs_id}`, `{genre}`, `{style}`, `{country}`

### Vinyl Position Logic (`calculate_track_and_disc`)

Returns `(track_number, disc_number)` as strings. Behaviour depends on two enums:

- **TrackNumbering**: `NUMERIC` = sequential 1,2,3; `ORIGINAL` = preserve Discogs position (A1,B1); `PER_SIDE` = reset count per side
- **DiscMapping**: `SINGLE` = always disc 1; `PER_SIDE` = each side is its own disc (A=1,B=2); `PHYSICAL` = group sides into physical discs (A+B=1, C+D=2); `ORIGINAL` = always disc 1

### Auth Chain (in `DiscogsClient.__init__`)

Tried in order (first match wins). When `auth_mode` is `auto`, all are attempted:

1. **`oauth`** — Full OAuth 1.0a (needs consumer_key, consumer_secret, token, secret)
2. **`token`** — Personal access token (needs token only)
3. **`key_secret`** — Consumer key/secret without user token (limited access, used for login prep)
4. **`none`** — Unauthenticated (fallback)

### `write_release_info()`

In `tagging.py`. Writes a structured plain-text file (default `release_info.txt`) with sections: header, release info (label, country, date, genres, formats), tracklist, companies, credits, identifiers, notes. Non-fatal on `OSError`.

### Tagging Overview

32 tags total gated by `_should_write(canonical_name, skip_tags)` — a simple `not in` check. See `docs/tag-mapping.md` for the full tag list with ID3/Vorbis field names.

## Logging

Uses **loguru** (`from loguru import logger`), not stdlib `logging`. `initialise_logging()` in `cli.py` configures two sinks:

1. **Console** — `sys.stderr` at `config.log_level`, colorized
2. **File** (if `config.log_to_file`) — DEBUG level to `platformdirs.user_log_dir("vinylkit") / "vinylkit.log"`, with rotation and retention

## Testing

### Fixtures (in `tests/conftest.py`)

- **`runner`**: `CliRunner` with config isolated via `VINYLKIT_CONFIG` env var pointing to `tmp_path`.
- **`mock_discogs`**: Patches `vinylkit.commands._helpers.{get_client, tag_audio_file, clear_audio_tags, write_release_info, save_artwork}`. Does NOT mock `move_file`/`move_directory` — tests that need file movement suppressed must patch those locally via `vinylkit.commands._helpers.move_file` etc.
- **`mp3_file` / `flac_file`**: Minimal valid audio files for round-trip tagging tests.
- **`create_mock_release()`**: Helper function (not a fixture) for building `DiscogsRelease` objects with defaults. Images default to `[]`; use `object.__setattr__` to add them.
- **`_suppress_loguru_file_sink`**: Autouse session fixture — calls `logger.remove()` to prevent file I/O during tests.
- **`_isolate_cache_dir`**: Autouse fixture — monkeypatches `vinylkit.discogs.get_cache_dir` to return `tmp_path / "cache"`.
- **`caplog`**: Overrides pytest's built-in — bridges loguru to `caplog.handler` so log assertions work normally.

### Conventions

- Every new feature or bug fix must include tests.
- **Test organization**: Tests belong in the existing file that matches their logical subject — e.g., tagging unit tests go in `test_tagging.py`, Discogs API tests in `test_discogs.py`, naming/move tests in `test_naming.py`, etc. Never create ad-hoc files like `test_bugfixes.py` or `test_fixes_round2.py`. If no existing file fits, create one named after the module or feature (e.g., `test_<module>.py`).
- Real audio fixtures (`_make_mp3_bytes`, `_make_flac_bytes`) create minimal valid files — no test data files on disk.
- API calls are always mocked. `respx` is available for HTTP-level mocking in `test_discogs.py`.
- **Test data isolation**: ALL test data MUST be written to `tmp_path` or equivalent temporary directories — never to real platform directories (cache, config, logs). The autouse `_isolate_cache_dir` fixture in `conftest.py` redirects the cache dir for every test. If a new module introduces platform-specific directories, add a similar autouse fixture to prevent leakage.

## Development Workflow Requirements

### After Every Feature or Bug Fix

1. **Write tests first or alongside the change.** Every new behavior needs a test case.
2. **Documentation sweep**: Check ALL `docs/*.md` files for any content that needs updating. Key docs and what they cover:
   - `configuration.md` — authoritative reference for ALL settings AND command flags. Every new config key, CLI flag, and option MUST be documented here with allowed values and at least one example.
   - `user-guide.md` — authoritative command and feature reference
   - `examples.md` — real-world command examples. Every new command and every new flag MUST have at least one example.
   - `developer-guide.md` — architecture, test patterns, dev setup
   - `data-model.md` — data structures and schemas
   - `spec.md` — original project specification
   - `auth.md`, `quickstart.md` — if auth or setup flow changed
3. **Example parity**: Any new example added to `docs/examples.md` MUST have a corresponding test in `tests/test_examples_coverage.py`.
4. **Flag coverage rule**: Every CLI flag/option introduced by a new command MUST be: (a) documented in `configuration.md` with allowed values and an example, (b) shown in at least one example in `examples.md`, and (c) covered by a test in `test_examples_coverage.py`.
5. **Run the full check suite** before considering work complete:

   ```bash
   uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy src/
   ```

### Code Style

- `from __future__ import annotations` in every file.
- All functions fully type-hinted; must pass `mypy --strict`.
- Line length: 88 characters.
- Destructive operations (rename, move, delete) default to dry-run or require confirmation.
