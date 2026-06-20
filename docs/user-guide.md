# VinylKit User Guide

A full guide to managing your vinyl rips with VinylKit.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
    - [The Library Root](#the-library-root)
    - [The Recordings Root (The Inbox)](#the-recordings-root-the-inbox)
3. [Command Reference](#3-command-reference)
    - [scan](#scan)
    - [tag](#tag)
    - [rename](#rename)
    - [migrate](#migrate)
    - [collection](#collection)
    - [auth](#auth)
    - [cache](#cache)
    - [config](#config)
4. [Configuration Options](#4-configuration-options)
5. [Naming Patterns & Placeholders](#5-naming-patterns--placeholders)
6. [Tagging Details](#6-tagging-details)
7. [Workflows](#7-workflows)
    - [The "Inbox" Workflow](#the-inbox-workflow)
    - [Manual Processing](#manual-processing)
8. [Logging](#8-logging)
9. [Common Gotchas](#9-common-gotchas)

---

> [!TIP]
> For a collection of real-world scenarios and command combinations using electronic music examples, see the **[Examples Guide](examples.md)**.

## Getting Help

Every command supports `-h` (or `--help`) to display detailed usage information, including available options and real-world examples:

```bash
vinylkit -h                # Overview, quick-start steps, command tree
vinylkit tag -h            # Tag options grouped by purpose, with examples
vinylkit config set -h     # Lists all valid configuration keys
vinylkit cache clear -h    # Shows examples for cache management
```

Options are grouped (like "Release Identification" or "Output Control") so you can find what you need.

---

## 1. Introduction

VinylKit helps organize your vinyl digitizations into a clean music library. It talks to the Discogs API to automate tagging files, downloading artwork, and organizing them into folders.

## 2. Core Concepts

### The Library Root

The `library_root` is where your organized music lives. When VinylKit renames or moves files, it uses this folder as the base.

### The Recordings Root (The Inbox)

The `recordings_root` is an optional "inbox" folder. By pointing this to the folder where your recording software exports files, you can run `vinylkit scan` or `vinylkit tag` without specifying a path.

### Safety & Overwrite Protection

VinylKit tries to keep your existing music library safe. Before moving or renaming files:

1. **Dry Run Support**: Every file-modifying command supports a `--dry-run` (or defaults to one in `rename`) so you can preview changes.
2. **Collision Detection**: If a generated path already has a file or folder, VinylKit stops and lists the conflicts.
3. **User Confirmation**: You'll be asked to confirm if you want to overwrite anything. If you decline, the move is canceled, keeping your files safe.

---

## 3. Command Reference

### `scan`

Scans directories for supported audio files (MP3, FLAC) and reports their status.

- **Usage**: `vinylkit scan [PATHS]...`
- **Behavior**: If no paths are provided, it scans `recordings_root`. If that isn't set, it scans `library_root`.

### `tag`

The main command for tagging files.

- **Usage**: `vinylkit tag [PATHS]... [OPTIONS]`
- **Options**:
  - `--id <ID[,ID,...]>`: Direct Discogs Release ID, or a comma-separated list
    of IDs. When multiple IDs are given, each must have a folder named by its ID
    in the library root, recordings root, or an explicit search path (e.g.
    `391682/`). You can pass a single PATH to use as the search root:
    `vinylkit tag /path/to/unsorted --id 182338,74044 ...`.
    A single ID falls back to `recordings_root` if no named folder is found.
  - `--search <TEXT>`: Global search query for interactive selection.
  - `--artist <TEXT>`: Filter search by artist name.
  - `--album <TEXT>`: Filter search by album/release title.
  - `--format <TEXT>`: Filter search by media format (e.g., Vinyl, CD).
  - `--auto-move`: Automatically move files without confirmation.
  - `--dry-run`: Preview changes without writing tags or moving files.
  - `--no-artwork`: Skip downloading and embedding artwork.
  - `--rename / --no-rename`: Enable or disable the move-to-library step. (Defaults to true if using `recordings_root`).
  - `--batch`: Batch mode — iterate immediate subfolders, extract Discogs IDs
    from folder names (`Album [12345]`, bare `12345`, or `12345-Artist-Title`),
    and tag each automatically. Combine with `--interactive` to trigger an interactive
    search for any folder lacking an ID. Incompatible with `--id`, `--search`,
    `--artist`, `--album`.
  - `--no-move`: Rename files in place but skip moving them to the library.
    Mutually exclusive with `--auto-move`.
  - `--delete-source`: Delete the source folder after files are successfully moved to the library.
  - `--merge`: Preserve existing tags that aren't overwritten by Discogs.
  - `--library-root <PATH>`: Temporary override for the library destination.

#### Batch Mode Quick Reference

| Command | Tag | Rename | Move to library |
|---------|-----|--------|-----------------|
| `--batch --no-rename` | yes | no | no |
| `--batch --no-move` | yes | yes | no |
| `--batch` | yes | yes | prompted (auto if `auto_move` config is `true`) |
| `--batch --auto-move` | yes | yes | yes (override, no prompt) |

### `rename`

Organizes files that are already tagged, without fetching metadata again.

- **Usage**: `vinylkit rename [PATHS]... [OPTIONS]`
- **Options**:
  - `--id <INTEGER>`: Discogs Release ID for path generation. Prompted interactively if not provided.
  - `--commit`: Required to actually move files (defaults to dry-run).
  - `--library-root <PATH>`: Temporary override for the library destination.

### `migrate`

Copies or moves an existing library folder into the new structure.

- **Usage**: `vinylkit migrate <SOURCE_DIR> <DEST_DIR> [OPTIONS]`
- **Behavior**:
  - Processes folders in alphabetical order.
  - Extracts Discogs IDs from folder names matching: bracket suffix `Album Name [12345]`, bare numeric `12345`, or URL-style prefix `12345-Artist-Album`.
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

Manages your Discogs collection.

- `collection download`: Fetches your entire collection from Discogs and saves it as a date-prefixed CSV file (e.g., `2026-02-08_auzziehood_collection.csv`). Warns if the file already exists.

### `auth`

Manages your Discogs credentials.

- `auth login`: Starts the OAuth process in your browser.
- `auth identity`: Displays the currently logged-in user.

> [!IMPORTANT]
> `auth login` requires `consumer_key` and `consumer_secret` to be configured first. For most users, setting a personal access token via `vinylkit config set discogs_token <TOKEN>` (and optionally `discogs_secret`) is simpler. See the **[Authentication Guide](auth.md)** for details.

### `cache`

Manages cached Discogs API responses on your computer.

- `cache list`: Lists all cached releases with ID, artist, album, and age.
- `cache clear`: Deletes all cached releases (prompts for confirmation).
  - `--id <INTEGER>`: Clear a single release by its Discogs ID.
  - `--yes` / `-y`: Skip the confirmation prompt.

### `config`

Manages your settings.

- `config show`: Displays the VinylKit version, all current settings, and the config file path.
- `config set <KEY> <VALUE>`: Updates a setting.
- `config reset`: Resets all configuration settings back to factory defaults (deleting your custom `config.toml` file).

### `--version`

Displays the installed VinylKit version.

- **Usage**: `vinylkit --version`

### Interactive Search

If you don't have a Release ID, you can search Discogs using one of two methods:

#### 1. Global Search (`--search`)

This is a "catch-all" search. Discogs tries to find your terms anywhere in the release metadata (artist, title, label, etc.).

- **Usage**: `vinylkit tag --search "Green Velvet Flash Remixes"`
- **Best for**: Quick searches when you only have a fragment of information.

#### 2. Filtered Search (`--artist`, `--album`, `--format`)

This is the most precise method. It tells Discogs exactly which fields to match, which reduces irrelevant results.

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
| `{artist}` | Release primary artist(s) |
| `{track_artist}` | Track-specific artist(s) |
| `{title}` | Track title |
| `{full_title}` | Track title (prefixed with artist if different from release artist) |
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
3. Run `vinylkit tag --id 12345` to tag and move the album to your library in one step. (`--rename` is automatic when using the inbox — no paths + `recordings_root` set.)

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
| --- | --- |
| **Windows** | `%LOCALAPPDATA%\vinylkit\vinylkit\Logs\vinylkit.log` |
| **macOS** | `~/Library/Logs/vinylkit/vinylkit.log` |
| **Linux** | `~/.local/state/vinylkit/log/vinylkit.log` |

### Customising Logging

For all logging settings (`log_level`, `log_to_file`, `log_file`, `log_rotation`, `log_retention`) with defaults, allowed values, and examples, see the **[Configuration Guide — Logging](configuration.md#logging)**.

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
