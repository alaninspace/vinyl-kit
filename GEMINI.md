# vinyl-kit Development Guidelines

## Project Overview

`vinylkit` is a cross-platform CLI tool for managing digitized vinyl record audio files. It leverages metadata from Discogs to tag, organize, and maintain a high-quality digital music collection.

- **Purpose**: Automate tagging and organization of vinyl rips using Discogs metadata.
- **Main Features**:
    - Discogs integration (search and release lookup).
    - Audio tagging for MP3 (ID3v2) and FLAC (Vorbis comments).
    - Vinyl-specific metadata support (side, position).
    - Safe file renaming and reorganization with dry-run support.
    - Artwork management (embedding).
    - Workflow optimization via `recordings_root` (inbox folder).
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
    ├── cli.py         # CLI entry point and command definitions
    ├── config.py      # Configuration loading and saving logic
    ├── discogs.py     # Discogs API client and authentication
    ├── exceptions.py  # Custom exception classes
    ├── models.py      # Pydantic-like data models and Enums
    ├── naming.py      # Filename generation and sanitization (Default: {artist}/{year} - {album}/...)
    ├── tagging.py     # Audio file tagging and scanning logic
    └── utils.py       # Helper functions (backups, etc.)
tests/                 # Comprehensive test suite
docs/                  # Documentation (spec, auth, quickstart, configuration)
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
