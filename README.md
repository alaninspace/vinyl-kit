# VinylKit

VinylKit is a cross-platform CLI tool for managing digitized vinyl record audio files using metadata from Discogs. It helps you tag, organize, and maintain your collection with high-quality metadata.

## Features

- **Discogs Integration**: Fetch high-quality metadata (Genres, Styles, Notes) using Release IDs or interactive search.
- **Combined Workflow**: Tag, rename and move files to your library in a single step.
- **Support for MP3 and FLAC**: Comprehensive tagging for ID3v2 and Vorbis comments.
- **Vinyl-Specific Metadata**: Preserves vinyl-specific info like side (A/B) and position (A1, B2).
- **Metadata Export**: Automatically creates a `release_info.txt` file in every tagged album folder with all the discogs release info.
- **Safe Operations**: Optional dry-runs, filename sanitization, and atomic file moves.
- **Batch Processing**: Tag or rename multiple folders in one go.
- **Artwork Management**: Embed album art directly into audio files (retrieved from Discogs).
- **Flexible Organization**: Use customizable naming templates to organize your library.
- **Collection Export**: Download your entire Discogs collection to a local CSV file.

## Installation

VinylKit requires Python 3.12+ and is managed with `uv`.

### As a Global Tool (Recommended)
This makes the `vinylkit` command available everywhere in your terminal.

```bash
git clone https://github.com/alaninspace/vinyl-man.git
cd vinyl-man
uv tool install . --force
```

### Updating
To update to the latest version after pulling changes:
```bash
uv tool install . --force --no-cache
```

## Quick Start

1. **Authenticate with Discogs**:
   ```bash
   vinylkit auth login
   ```

2. **Scan a folder**:
   ```bash
   vinylkit scan /path/to/music
   ```

3. **Tag and Organize an album by ID**:
   ```bash
   # Green Velvet - Flash (Remixes)
   vinylkit tag /path/to/album --id 19983 --rename
   ```

4. **Tag using Search**:
   ```bash
   # The Prodigy - Out Of Space
   vinylkit tag /path/to/album --search "The Prodigy Out Of Space" --rename
   ```

## Configuration

Settings are stored in a platform-appropriate TOML file. You can view your current config with:

```bash
vinylkit config show
```

For detailed guides, see:
- **[Quick Start](docs/quickstart.md)**: Setup and basic workflow.
- **[User Guide](docs/user-guide.md)**: In-depth command and feature reference.
- **[Examples](docs/examples.md)**: Real-world command combinations.
- **[Configuration Guide](docs/configuration.md)**: Full list of all settings.

## Development

VinylKit uses `uv` for development. Ensure you have it installed.

### Run Tests
```bash
uv run pytest
```

### Linting & Formatting
```bash
# Check for linting errors
uv run ruff check .

# Fix linting errors automatically
uv run ruff check . --fix

# Format code
uv run ruff format .
```

### Type Checking
```bash
uv run mypy .
```