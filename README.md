# VinylKit

VinylKit is a cross-platform CLI tool for managing digitized vinyl record audio files using metadata from Discogs. It helps you tag, organize, and maintain your collection with high-quality metadata.

## Features

- **Discogs Integration**: Fetch high-quality metadata (Genres, Styles, Notes) using Release IDs or interactive search.
- **Combined Workflow**: Tag and rename files in a single step using the `--rename` flag.
- **Support for MP3 and FLAC**: Comprehensive tagging for ID3v2 and Vorbis comments.
- **Vinyl-Specific Metadata**: Preserves vinyl-specific info like side (A/B) and position (A1, B2).
- **Metadata Export**: Automatically creates a `release_info.txt` file in every tagged album folder.
- **Safe Operations**: Mandatory dry-runs, filename sanitization, and atomic file moves.
- **Batch Processing**: Tag or rename multiple folders in one go.
- **Artwork Management**: Embed album art directly into files and save cover images.
- **Flexible Organization**: Use customizable naming templates to organize your library.

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
   vinylkit tag /path/to/album --id 249504 --rename
   ```

4. **Tag using Search**:
   ```bash
   vinylkit tag /path/to/album --search "Pink Floyd Dark Side" --rename
   ```

## Configuration

Settings are stored in a platform-appropriate TOML file. You can view your current config with:

```bash
vinylkit config show
```

Key settings include:
- `library_root`: Default path for scans and organization.
- `naming_pattern`: Template for file paths (e.g., `{artist}/{album} ({year})/{track_number} - {title}`).
- `backup_enabled`: Whether to backup files before modification.

## Development

Run tests with `pytest`:

```bash
uv run pytest
```

Check code style with `ruff`:

```bash
uv run ruff check .
```