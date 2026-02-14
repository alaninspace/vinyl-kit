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
uv run mypy src/                     # type check (use src/, not .)
uv run vinylkit [COMMAND]            # run the CLI locally
```

## Known Pre-existing Warnings

These are expected and should NOT be "fixed":
- **mypy**: `mutagen` and `authlib` lack type stubs, producing `no-untyped-call` and `attr-defined` errors across `tagging.py` and `discogs.py`. Suppressed via `pyproject.toml` overrides.
- **ruff TC003**: Suggests moving imports to `TYPE_CHECKING` blocks, but `Path` is used in dataclass defaults so this is unsafe.
- **ruff SIM102**: Nested-if in `discogs.py` auth chain is intentional for readability.
- **ruff PERF401**: `list.append` in loops in `tagging.py` is clearer than `list.extend`.

## Architecture

### Data Flow

```
CLI command (click, ctx.obj=AppConfig)
  -> DiscogsClient (httpx sync)
    -> DiscogsRelease (frozen dataclass)
      -> tagging.py (write tags via mutagen)
      -> naming.py (generate paths, move/rename files)
```

### Module Responsibilities

| Module | Role |
|---|---|
| `cli.py` | Click commands, shared helpers (`_collect_audio_files`, `_plan_supplementary_moves`, `_check_collisions`), `_CONFIG_CONVERTERS` dict |
| `config.py` | TOML load/save. Explicit field-by-field mapping between TOML keys and `AppConfig` |
| `discogs.py` | API client, OAuth auth chain (auto/token/oauth/key_secret/none), response caching, rate limiting with exponential backoff |
| `models.py` | Frozen dataclasses (`AppConfig`, `DiscogsRelease`, `TrackInfo`, `ImageInfo`, `AudioFile`) and enums (`TagMode`, `ImageHandling`, `TrackNumbering`, `DiscMapping`, `AuthMode`) |
| `naming.py` | Filename templates, path generation, safe file/directory moves |
| `tagging.py` | MP3 (ID3v2) and FLAC (Vorbis) tagging, artwork embedding/saving, `calculate_track_and_disc()` for vinyl position logic |
| `utils.py` | File backup, filename sanitization (NFC normalization, illegal char removal, UTF-8 truncation) |
| `exceptions.py` | Hierarchy: `VinylkitError` -> `ConfigError`, `AuthError`, `DiscogsAPIError`, `TaggingError`, `FileOperationError`, `ValidationError` |

### Key Patterns

- **Config system**: `load_config()` reads TOML and manually maps to `AppConfig` frozen dataclass. `_CONFIG_CONVERTERS` dict maps config keys to converter functions for `config set`.
- **Error handling**: Custom exceptions for user-facing errors (caught in `main()`). Use `logger.warning` for recoverable issues. Catch specific types (`OSError`, `DiscogsAPIError`), never bare `Exception`.
- **All models are frozen**: `@dataclass(slots=True, frozen=True)`. Use `object.__setattr__` in tests when you need to override fields.
- **`FRONT_COVER_TYPE = 3`**: Constant in `tagging.py` for ID3 APIC and FLAC Picture type.
- **Artwork naming**: Primary image in music folder uses `config.artwork_filename` (e.g., `folder.jpg`). Collected artwork in subdir uses `primary_01.jpg`, `secondary_01.jpg`, `secondary_02.jpg`, etc.

## Testing

### Fixtures (in `tests/conftest.py`)

- **`runner`**: `CliRunner` with config isolated via `VINYLKIT_CONFIG` env var pointing to `tmp_path`.
- **`mock_discogs`**: Patches `get_client`, `tag_audio_file`, `clear_audio_tags`, `write_release_info`, `save_artwork`. Does NOT mock `move_file`/`move_directory` — tests that need file movement suppressed must patch those locally.
- **`mp3_file` / `flac_file`**: Minimal valid audio files for round-trip tagging tests.
- **`create_mock_release()`**: Helper function (not a fixture) for building `DiscogsRelease` objects with defaults. Images default to `[]`; use `object.__setattr__` to add them.

### Conventions

- Every new feature or bug fix must include tests.
- Real audio fixtures (`_make_mp3_bytes`, `_make_flac_bytes`) create minimal valid files — no test data files on disk.
- API calls are always mocked. `respx` is available for HTTP-level mocking in `test_discogs.py`.

## Development Workflow Requirements

### After Every Feature or Bug Fix

1. **Write tests first or alongside the change.** Every new behavior needs a test case.
2. **Documentation sweep**: Check ALL `docs/*.md` files for any content that needs updating. Key docs and what they cover:
   - `configuration.md` — authoritative config key reference (new settings MUST be added here)
   - `user-guide.md` — authoritative command and feature reference
   - `examples.md` — real-world command examples
   - `developer-guide.md` — architecture, test patterns, dev setup
   - `data-model.md` — data structures and schemas
   - `auth.md`, `quickstart.md` — if auth or setup flow changed
3. **Example parity**: Any new example added to `docs/examples.md` MUST have a corresponding test in `tests/test_examples_coverage.py`.
4. **Run the full check suite** before considering work complete:
   ```bash
   uv run pytest && uv run ruff check . && uv run ruff format --check .
   ```

### Code Style

- `from __future__ import annotations` in every file.
- All functions fully type-hinted; must pass `mypy --strict`.
- Line length: 88 characters.
- Destructive operations (rename, move, delete) default to dry-run or require confirmation.
