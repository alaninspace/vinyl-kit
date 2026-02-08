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
    - `--id <INTEGER>`: Required to know the metadata for path generation.
    - `--commit`: Required to actually move files (defaults to dry-run).

### `collection`
Manages your Discogs collection data.

- `collection download`: Fetches your entire collection from Discogs and saves it as a date-prefixed CSV file (e.g., `2026-02-08_auzziehood_collection.csv`). Warns if the file already exists.

### `auth`
Manages your connection to Discogs.

- `auth login`: Starts the OAuth process in your browser.
- `auth identity`: Displays the currently logged-in user.

> [!IMPORTANT]
> `auth login` requires `consumer_key` and `consumer_secret` to be configured first. For most users, setting a personal access token via `vinylkit config set discogs_token <TOKEN>` is simpler. See the **[Authentication Guide](auth.md)** for details.

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

- **General** — `library_root`, `recordings_root`, `auto_move`, `auth_mode`
- **Tagging & Numbering** — `tag_mode`, `track_numbering`, `disc_mapping`
- **Naming & Organization** — `naming_pattern`
- **Artwork & Metadata** — `image_handling`, `artwork_filename`, `collect_all_artwork`, `artwork_subdir`, `info_filename`
- **Search & Discovery** — `search_page_size`, `default_format`
- **Safety & Backups** — `backup_enabled`, `backup_dir`

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

---

## 6. Tagging Details

### MP3 (ID3v2.4)
VinylKit writes the following frames:
- `TPE1`: Artist
- `TIT2`: Title
- `TALB`: Album
- `TDRC`: Year
- `TRCK`: Track Number
- `TPOS`: Disc Number
- `TPUB`: Publisher (Label)
- `TCON`: Genre
- `TXXX (STYLE)`: Style
- `TXXX (DISCOGS_POSITION)`: Original vinyl position
- `TXXX (SIDE)`: Vinyl side
- `APIC`: Front Cover

### FLAC (Vorbis Comments)
VinylKit writes the following tags:
- `artist`, `title`, `album`, `date`, `tracknumber`, `discnumber`, `organization` (Label), `genre`, `style`, `discogs_position`, `side`.

---

## 7. Workflows

### The "Inbox" Workflow
1. Set `recordings_root` to your export folder.
2. Run `vinylkit scan` to verify files are present.
3. Run `vinylkit tag --id 12345` to tag and move the album to your library in one step.

### Manual Processing
1. Run `vinylkit tag "/path/to/folder" --search "Artist Name"`
2. Follow the interactive prompts to select the correct release.
3. Use `--rename` if you want VinylKit to move the files for you.

---

## 8. Common Gotchas

### Multi-word searches
Always wrap multi-word search queries in quotes. Without quotes, the CLI will treat the second word as a folder path.
- **Incorrect**: `vinylkit tag --search Green Velvet`
- **Correct**: `vinylkit tag --search "Green Velvet"`

### Path order
If you are providing a specific path AND a search query, the path usually comes after the options or before them depending on your shell, but the safest way is:
`vinylkit tag "/path/to/music" --search "Query"`
