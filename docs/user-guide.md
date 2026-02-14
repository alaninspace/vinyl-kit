# VinylKit User Guide

A comprehensive guide to managing your digitized vinyl collection with VinylKit.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
    - [The Library Root](#the-library-root)
    - [The Recordings Root (The Inbox)](#the-recordings-root)
3. [Command Reference](#3-command-reference)
    - [scan](#scan)
    - [tag](#tag)
    - [rename](#rename)
    - [migrate](#migrate)
    - [auth](#auth)
    - [config](#config)
4. [Configuration Options](#4-configuration-options)
5. [Naming Patterns & Placeholders](#5-naming-patterns--placeholders)
6. [Tagging Details](#6-tagging-details)
    - [MP3 (ID3v2.4)](#mp3-id3v24)
    - [FLAC (Vorbis Comments)](#flac-vorbis-comments)
7. [Workflows](#7-workflows)
    - [The "Inbox" Workflow](#the-inbox-workflow)
    - [Manual Processing](#manual-processing)

---

> [!TIP]
> For a collection of real-world scenarios and command combinations using electronic music examples, see the **[Examples Guide](examples.md)**.

## 1. Introduction

VinylKit is designed to bridge the gap between high-quality vinyl digitizations and organized digital music libraries. By leveraging the Discogs API, it automates the tedious process of tagging files with accurate metadata, downloading artwork, and organizing them into a clean folder structure.

## 2. Core Concepts

### The Library Root
The `library_root` is the final destination for your music. When VinylKit renames or moves files, it uses this directory as the base. 

### The Recordings Root (The Inbox)
The `recordings_root` is an optional but highly recommended "inbox". By pointing this to the folder where your recording software exports files, you can run `vinylkit scan` or `vinylkit tag` without specifying a path.

### Safety & Overwrite Protection
VinylKit prioritizes the safety of your existing music library. Before performing any move or rename operation:
1. **Dry Run Support**: Every destructive command supports a `--dry-run` or defaults to one (in `rename`) to show you exactly what will happen.
2. **Collision Detection**: If the generated destination path already contains a file or folder, VinylKit will halt and display a warning list of all affected items.
3. **User Confirmation**: You will be prompted to explicitly confirm if you want to overwrite existing files. If you decline, the entire move operation for that folder is aborted, keeping your library and your original files intact.

---

## 3. Command Reference

### `scan`
Scans directories for supported audio files (MP3, FLAC) and reports their status.

- **Usage**: `vinylkit scan [PATHS]...`
- **Behavior**: If no paths are provided, it scans `recordings_root`. If that isn't set, it scans `library_root`.

### `tag`
The primary command for applying metadata to your files.

- **Usage**: `vinylkit tag [PATHS]... [OPTIONS]`
- **Options**:
    - `--id <INTEGER>`: Direct Discogs Release ID.
    - `--search <TEXT>`: Global search query for interactive selection.
    - `--artist <TEXT>`: Filter search by artist name.
    - `--album <TEXT>`: Filter search by album/release title.
    - `--format <TEXT>`: Filter search by media format (e.g., Vinyl, CD).
    - `--auto-move`: Automatically move files without confirmation.
    - `--dry-run`: Preview changes without writing tags or moving files.
    - `--no-artwork`: Skip downloading and embedding artwork.
    - `--rename / --no-rename`: Enable or disable the move-to-library step. (Defaults to true if using `recordings_root`).
    - `--merge`: Preserve existing tags that aren't overwritten by Discogs.
    - `--library-root <PATH>`: Temporary override for the library destination.

### `rename`
Organizes already-tagged files into the library structure without re-tagging.

- **Usage**: `vinylkit rename [PATHS]... [OPTIONS]`
- **Options**:
    - `--id <INTEGER>`: Discogs Release ID for path generation. Prompted interactively if not provided.
    - `--commit`: Required to actually move files (defaults to dry-run).
    - `--library-root <PATH>`: Temporary override for the library destination.

### `migrate`
Migrates an existing library to the new structure.

- **Usage**: `vinylkit migrate <SOURCE_DIR> <DEST_DIR> [OPTIONS]`
- **Behavior**:
    - Processes folders in alphabetical order.
    - Extracts Discogs IDs from folder names matching the pattern `... [ID]` (e.g., `Album Name [12345]`).
    - Prompts for ID if not found in the name.
    - Maps files to Discogs tracklists using existing tags (track numbers) or alphabetical order.
    - Non-destructive by default (copies files).
    - Generates a detailed log file `00-Migration-Results.txt` in the destination directory.
- **Progress Tracking**: Each folder displays a progress header like `[1/10] Migrating: Album Name (0%)`. The total is recalculated dynamically by re-scanning the source directory before each release, so it adjusts automatically if folders are added or removed during migration.
- **Smart Throttling**: The migrate command dynamically adjusts API request delays based on remaining rate limit headroom (from Discogs `X-Discogs-Ratelimit-Remaining` headers). When headroom is high, requests are faster; as limits approach, delays increase automatically. Rate limit snapshots are logged to `00-Migration-Results.txt` during migration, along with a summary at the end.
- **Options**:
    - `--delete`: Delete source folders after successful migration (Default: False).
    - `--replace-artwork`: Replace existing artwork in tags with fresh downloads (Default: uses config `replace_artwork_on_migration`).
    - `--replace-tags`: Clear and re-write audio tags from Discogs metadata (Default: uses config `replace_tags_on_migration`). When not set, files are copied without tag modifications.
    - `--id <TEXT>`: Only migrate specific Discogs IDs (comma-separated list).
    - `--dry-run`: Preview the migration and mapping without touching any files.

### `collection`
Manages your Discogs collection data.

- `collection download`: Fetches your entire collection from Discogs and saves it as a date-prefixed CSV file (e.g., `2026-02-08_auzziehood_collection.csv`). Warns if the file already exists.

### `auth`
Manages your connection to Discogs.

- `auth login`: Starts the OAuth process in your browser.
- `auth identity`: Displays the currently logged-in user.

> [!IMPORTANT]
> `auth login` requires `consumer_key` and `consumer_secret` to be configured first. For most users, setting a personal access token via `vinylkit config set discogs_token <TOKEN>` (and optionally `discogs_secret`) is simpler. See the **[Authentication Guide](auth.md)** for details.

### `cache`
Manages the Discogs API response cache stored in the platform cache directory.

- `cache list`: Lists all cached releases with ID, artist, album, and age.
- `cache clear`: Deletes all cached releases (prompts for confirmation).
  - `--id <INTEGER>`: Clear a single release by its Discogs ID.
  - `--yes` / `-y`: Skip the confirmation prompt.

### `config`
Manages your persistent settings.

- `config show`: Displays all current settings and the config file path.
- `config set <KEY> <VALUE>`: Updates a setting.

### Interactive Search
If you don't have a Release ID, you can search Discogs using one of two methods:

#### 1. Global Search (`--search`)
This is a "catch-all" search. Discogs tries to find your terms anywhere in the release metadata (artist, title, label, etc.).
- **Usage**: `vinylkit tag --search "Green Velvet Flash Remixes"`
- **Best for**: Quick searches when you only have a fragment of information.

#### 2. Filtered Search (`--artist`, `--album`, `--format`)
This is the **recommended** method for precision. It tells Discogs exactly which fields to match, which drastically reduces irrelevant results.
- **Usage**: `vinylkit tag --artist "Faithless" --album "Insomnia"`
- **Best for**: Common artist names or finding specific pressings.

#### The Search Interface
When you search, VinylKit presents a formatted table with:
- **ID**: The Discogs Release ID.
- **Title**: Artist and Album name.
- **Year/Country/Format**: Essential metadata to help you identify the correct pressing.
- **Link**: A direct web link to the Discogs page for that release.

#### Pagination & Navigation
When viewing results, you can use the following commands:
- `m`: See more results (next page).
- `r`: **Re-search**. Discard current results and enter a new query for this folder.
- `0`: **Skip** this folder and move to the next one in the batch.
- `q`: **Quit** the entire tagging session and exit.
- `<NUMBER>`: Select the release by its row number (e.g., `1`).

#### Tips for Best Results
- **Use Filters First**: Always prefer `--artist` and `--album` over a general `--search` for faster, cleaner results.
- **Use the Catalog Number**: Searching for the ID on the vinyl spine (e.g., `vinylkit tag --search "RR001"`) is often the most accurate way to find your exact pressing.
- **Format Filtering**: By default, VinylKit filters for "Vinyl". To override this, use `--format "CD"` or `--format "File"`.

---

## 4. Configuration Options

VinylKit's settings are grouped into the following categories:

- **General** — `library_root`, `recordings_root`, `auto_move`
- **Cache** — `cache_enabled`
- **Tagging & Numbering** — `tag_mode`, `track_numbering`, `disc_mapping`, `skip_tags`
- **Naming & Organization** — `naming_pattern`
- **Artwork & Metadata** — `image_handling`, `artwork_filename`, `collect_all_artwork`, `artwork_subdir`, `info_filename`
- **Search & Discovery** — `search_page_size`, `default_format`
- **Safety & Backups** — `backup_enabled`, `backup_dir`
- **Library Migration** — `delete_after_migration`, `replace_artwork_on_migration`, `replace_tags_on_migration`
- **Logging** — `log_level`, `log_to_file`, `log_file`, `log_rotation`, `log_retention`
- **Authentication** — `auth_mode`, `consumer_key`, `consumer_secret`, `discogs_token`, `discogs_secret`

For defaults, allowed values, and examples for every setting, see the **[Configuration Guide](configuration.md)**.

---

## 5. Naming Patterns & Placeholders

You can customize your library structure using the following placeholders in `naming_pattern`:

| Placeholder | Description |
| :--- | :--- |
| `{artist}` | Primary artist(s) |
| `{album}` | Release title |
| `{year}` | Release year |
| `{track_number}` | Calculated track number |
| `{title}` | Track title |
| `{side}` | Vinyl side (A, B, etc.) |
| `{label}` | Primary label |
| `{catalogue_number}` | Primary catalog number |
| `{genre}` | Primary genre |
| `{style}` | Primary style |
| `{country}` | Release country |
| `{id}` | Discogs Release ID |
| `{discogs_id}` | Alias for `{id}` |

---

## 6. Tagging Details

VinylKit writes up to **32 tags** per audio file, covering standard metadata, ecosystem-recognized fields, and Discogs-specific data. For the complete mapping of every tag including its MP3 frame, FLAC key, and data source, see the **[Tag Mapping Reference](tag-mapping.md)**.

### Highlights

- **Standard tags**: artist, albumartist, title, album, date, releasedate, tracknumber, discnumber, publisher, genre, composer, remixer, copyright, media, artistsort
- **Ecosystem tags**: style, catalognumber, side, label, format, companies, credits, barcode, country, discogs_position
- **Discogs-specific**: discogs_release_id, discogs_release_url, discogs_master_id, discogs_master_url, discogs_notes, discogs_data_quality, discogs_format_quantity
- **Artwork**: Front cover embedded as APIC (MP3) or PICTURE (FLAC)

### Controlling Tags

You can exclude any tag using the `skip_tags` config setting:

```bash
# Skip genre and style
vinylkit config set skip_tags "genre,style"

# Clear the skip list (write all tags)
vinylkit config set skip_tags "none"
```

---

## 7. Workflows

### The "Inbox" Workflow
1. Set `recordings_root` to your export folder.
2. Run `vinylkit scan` to verify files are present.
3. Run `vinylkit tag --id 12345` to tag and move the album to your library in one step.

### Manual Processing

**Bash:**
1. Run `vinylkit tag ~/path/to/folder --search "Artist Name"`
2. Follow the interactive prompts to select the correct release.
3. Use `--rename` if you want VinylKit to move the files for you.

**PowerShell:**
1. Run `vinylkit tag "C:\Path\To\Folder" --search "Artist Name"`
2. Follow the interactive prompts to select the correct release.
3. Use `--rename` if you want VinylKit to move the files for you.

---

## 8. Logging

VinylKit uses **loguru** for dual-sink logging:

- **Console sink**: Displays messages at the configured `log_level` (default: `INFO`). Shows release separators and summaries for a clean user experience. Per-file operations (tagging, moving, artwork saving) are `DEBUG`-level and hidden from the console by default.
- **File sink**: Writes detailed diagnostic logs (always at `DEBUG` level) to a rotating log file, including timestamps, module names, and line numbers. The log file is structured with release separators (`=== Release: ... ===`), per-file debug entries, and rate limit snapshots for easy review. Enabled by default.

### Default Log File Location

The log file is stored in the platform-specific log directory:

| Platform | Default Path |
|---|---|
| **Windows** | `%LOCALAPPDATA%\vinylkit\Logs\vinylkit.log` |
| **macOS** | `~/Library/Logs/vinylkit/vinylkit.log` |
| **Linux** | `~/.local/state/vinylkit/log/vinylkit.log` |

### Customising Logging

```bash
# Show more detail in the console
vinylkit config set log_level DEBUG

# Disable file logging entirely
vinylkit config set log_to_file false

# Use a custom log file path
vinylkit config set log_file ~/logs/vinylkit.log

# Change rotation size (default: "5 MB")
vinylkit config set log_rotation "10 MB"

# Keep fewer rotated files (default: 5)
vinylkit config set log_retention 3
```

---

## 9. Common Gotchas

### Multi-word searches
Always wrap multi-word search queries in quotes. Without quotes, the CLI will treat the second word as a folder path.
- **Incorrect**: `vinylkit tag --search Green Velvet`
- **Correct**: `vinylkit tag --search "Green Velvet"`

### Path order
If you are providing a specific path AND a search query, the path usually comes after the options or before them depending on your shell, but the safest way is:

**Bash:**
`vinylkit tag ~/path/to/music --search "Query"`

**PowerShell:**
`vinylkit tag "C:\Path\To\Music" --search "Query"`
