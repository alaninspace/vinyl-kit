# vinyl-kit Development Guidelines

## Project Overview

`vinylkit` is a cross-platform CLI tool for managing digitized vinyl record audio files. It leverages metadata from Discogs to tag, organize, and maintain a high-quality digital music collection.

- **Purpose**: Automate tagging and organization of vinyl rips using Discogs metadata.
- **Main Features**:
    - Discogs integration (search by ID, free-text, or filtered `--artist`/`--album`/`--format`).
    - Audio tagging for MP3 (ID3v2) and FLAC (Vorbis comments), with replace and merge modes.
    - Vinyl-specific metadata support (side, position, track numbering, disc mapping).
    - Safe file renaming and reorganization with dry-run support.
    - Artwork management (embed, save, or both; optional full artwork collection).
    - Metadata export (`release_info.txt` generated per album).
    - Collection export (download full Discogs collection as CSV).
    - Workflow optimization via `recordings_root` (inbox folder) with auto-move.
    - Mandatory dry-runs for destructive operations.

## Active Technologies

- **Language**: Python 3.12+ (utilizing modern syntax like `match` statements and `tomllib`).
- **Management**: `uv` (for dependency management and tool installation).
- **CLI Framework**: `click`.
- **Audio Tagging**: `mutagen`.
- **API Client**: `httpx` with `authlib` for Discogs OAuth.
- **UI/Formatting**: `rich` (for tables, progress bars, and logging).
- **Configuration**: `platformdirs` (config location) and `tomli-w` (TOML writing).
- **Testing**: `pytest`, `pytest-mock`, `respx` (API mocking).
- **Linting/Formatting**: `ruff`.
- **Type Checking**: `mypy` (strict mode).

## Project Structure

```text
src/
└── vinylkit/
    ├── __init__.py    # Package marker
    ├── __main__.py    # Allows `python -m vinylkit`
    ├── cli.py         # CLI entry point and command definitions (~920 lines)
    ├── config.py      # Configuration loading/saving (TOML via tomllib/tomli-w)
    ├── discogs.py     # Discogs API client, OAuth, caching
    ├── exceptions.py  # Custom exception classes
    ├── models.py      # Dataclasses, Enums (AppConfig, DiscogsRelease, etc.)
    ├── naming.py      # Filename generation and sanitization
    ├── tagging.py     # Audio file tagging, scanning, artwork embedding
    └── utils.py       # Helper functions (backups, etc.)
tests/                 # Comprehensive test suite
docs/
    ├── auth.md            # Authentication guide (token & OAuth)
    ├── configuration.md   # Full config key reference (authoritative)
    ├── data-model.md      # Data model documentation
    ├── developer-guide.md # Developer setup and architecture
    ├── examples.md        # Real-world command examples
    ├── quickstart.md      # Setup walkthrough (links out for depth)
    ├── spec.md            # Internal specification
    └── user-guide.md      # Comprehensive command & feature reference (authoritative)
```

## Key Commands

### Development

- **Run CLI**: `uv run vinylkit [COMMAND]`
- **Run Tests**: `uv run pytest`
- **Linting**: `uv run ruff check .`
- **Type Checking**: `uv run mypy .`
- **Formatting**: `uv run ruff format .`

### Installation

- **Global Install**: `uv tool install . --force`
- **Update**: `uv tool install . --force --no-cache`

## CLI Commands

### Top-level Commands
- `vinylkit scan [PATHS]...` — Scan directories for audio files and report tagging status.
- `vinylkit tag [PATHS]... [OPTIONS]` — Tag files with Discogs metadata, optionally rename/move to library.
    - `--id <INT>`: Direct Discogs Release ID.
    - `--search <TEXT>`: Free-text search with interactive selection.
    - `--artist <TEXT>`, `--album <TEXT>`, `--format <TEXT>`: Filtered search.
    - `--rename / --no-rename`: Move files to library (auto-enabled from `recordings_root`).
    - `--merge`: Preserve existing tags (default is replace).
    - `--auto-move`: Skip move confirmation.
    - `--dry-run`, `--no-artwork`, `--library-root <PATH>`.
- `vinylkit rename [PATHS]... --id <INT>` — Move already-tagged files (dry-run by default, `--commit` to execute).

### Command Groups
- `vinylkit auth login` — Interactive OAuth flow (requires `consumer_key`/`consumer_secret`).
- `vinylkit auth identity` — Display authenticated Discogs user.
- `vinylkit config show` — Display all current settings.
- `vinylkit config set <KEY> <VALUE>` — Update a setting.
- `vinylkit collection download` — Export full Discogs collection as date-prefixed CSV.

## Development Conventions

- **Safety First**: Destructive operations (renaming, moving) should default to dry-run or require explicit confirmation.
- **Documentation**: ANY changes or new features MUST include updates to the relevant documentation (README, user-guide, etc.). ANY new examples added to `docs/examples.md` MUST have a corresponding test case in `tests/test_examples_coverage.py`.
- **Strict Typing**: All new code must be fully type-hinted and pass `mypy --strict`.
- **Code Style**: Follow PEP 8 via `ruff`. Line length is 88 characters.
- **Async/Sync**: Current architecture is synchronous for CLI simplicity, using `httpx` SyncClient.
- **Error Handling**: Use custom exceptions from `vinylkit.exceptions` for user-facing errors. Avoid leaking raw API or library exceptions to the CLI.
- **Testing**: Every new feature or bug fix should include corresponding tests in the `tests/` directory. Each change must be accompanied by at least one test case.

## Recent Changes

- **001-vinylkit-cli-manager**: Initial implementation of the CLI structure, Discogs integration, and tagging logic.
- **002-enhanced-tagging**: Search filters (`--artist`, `--album`, `--format`), auto-move option, collection download command.
- **003-expanded-metadata**: Track numbering modes, disc mapping strategies, merge tagging, metadata export (`release_info.txt`).
- **004-docs-overhaul**: Documentation accuracy and consistency fixes; established authority map across docs.
