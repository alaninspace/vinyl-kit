# VinylKit

[![Documentation](https://img.shields.io/badge/docs-vinylkit.app-blue)](https://vinylkit.app/)

VinylKit is a cross-platform CLI tool for managing digitized vinyl record audio files using metadata from Discogs. It helps you tag, organize, and maintain your collection with high-quality metadata.

## Features

- **Discogs Integration**: Fetch high-quality metadata (Genres, Styles, Notes) using Release IDs or interactive search.
- **Combined Workflow**: Tag, rename and move files to your library in a single step.
- **Support for MP3 and FLAC**: Comprehensive tagging for ID3v2 and Vorbis comments.
- **Vinyl-Specific Metadata**: Preserves vinyl-specific info like side (A/B) and position (A1, B2).
- **Metadata Export**: Automatically creates a `release_info.txt` file in every tagged album folder with all the discogs release info.
- **Safe Operations**: Optional dry-runs, filename sanitization, and atomic file moves.
- **Batch Processing**: Use `--batch` to automatically tag multiple folders, extracting Discogs IDs from folder names.
- **Artwork Management**: Embed album art directly into audio files (retrieved from Discogs).
- **Flexible Organization**: Use customizable naming templates to organize your library.
- **Collection Export**: Download your entire Discogs collection to a local CSV file.

## Installation

VinylKit requires Python 3.12+ and is managed with `uv`.

### As a Global Tool (Recommended)

This makes the `vinylkit` command available everywhere in your terminal.

```bash
git clone https://github.com/alaninspace/vinyl-kit.git
cd vinyl-kit
uv tool install . --force
```

### Updating

To update to the latest version after pulling changes:

```bash
uv tool install . --force --no-cache
```

## Quick Start

1. **Set your library location** (where tagged music ends up):

   ```bash
   vinylkit config set library_root "/path/to/VinylLibrary"
   ```

2. **Set your recordings inbox** (where fresh vinyl rips land):

   ```bash
   vinylkit config set recordings_root "/path/to/RecordedVinyl"
   ```

3. **Set your Discogs token** ([generate one here](https://www.discogs.com/settings/developers)):

   ```bash
   vinylkit config set discogs_token "YOUR_TOKEN"
   ```

4. **Scan and tag**:

   ```bash
   vinylkit scan
   vinylkit tag --id 19983
   ```

> [!TIP]
> For OAuth setup, naming patterns, and advanced configuration see the **[Quickstart Guide](docs/quickstart.md)**.

## Configuration

Settings are stored in a platform-appropriate TOML file. You can view your current config with:

```bash
vinylkit config show
```

For detailed interactive guides, visit **[vinylkit.app](https://vinylkit.app/)** or see the local documentation files:

- **[Quick Start](docs/quickstart.md)**: Setup and basic workflow.
- **[User Guide](docs/user-guide.md)**: In-depth command and feature reference.
- **[Examples](docs/examples.md)**: Real-world command combinations.
- **[Configuration Guide](docs/configuration.md)**: Full list of all settings.
- **[Developer Guide](docs/developer-guide.md)**: Setup, code architecture, and testing.
- **[Authentication Guide](docs/auth.md)**: Setting up Discogs credentials and OAuth.
- **[Tag Mapping Reference](docs/tag-mapping.md)**: Complete tag list with MP3/FLAC field names.
- **[Data Model Reference](docs/data-model.md)**: Data structures, database types, and schemas.
- **[Specification Spec](docs/spec.md)**: Product specs and technical requirements.

## Development

VinylKit uses `uv` for development. Ensure you have it installed. See the **[Developer Guide](docs/developer-guide.md)** for full setup, architecture, and contribution details.

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
uv run mypy src/
```
