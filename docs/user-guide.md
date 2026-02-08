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
    - [General Settings](#general-settings)
    - [Tagging & Numbering](#tagging--numbering)
    - [Naming & Organization](#naming--organization)
    - [Artwork & Metadata Files](#artwork--metadata-files)
    - [Safety & Backups](#safety--backups)
5. [Naming Patterns & Placeholders](#5-naming-patterns--placeholders)
6. [Tagging Details](#6-tagging-details)
    - [MP3 (ID3v2.4)](#mp3-id3v24)
    - [FLAC (Vorbis Comments)](#flac-vorbis-comments)
7. [Workflows](#7-workflows)
    - [The "Inbox" Workflow](#the-inbox-workflow)
    - [Manual Processing](#manual-processing)

---

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
    - `--search <TEXT>`: Search query for interactive selection.
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

### `auth`
Manages your connection to Discogs.

- `auth login`: Starts the OAuth process in your browser.
- `auth identity`: Displays the currently logged-in user.

### `config`
Manages your persistent settings.

- `config show`: Displays all current settings and the config file path.
- `config set <KEY> <VALUE>`: Updates a setting.

### Interactive Search
If you don't have a Release ID, you can search Discogs directly. **Note: Multi-word searches must be wrapped in quotes.**

- **Usage**: `vinylkit tag --search "Artist Name Album Title"`
- **Example**: `vinylkit tag --search "Green Velvet Destination Unknown"`

---

## 4. Configuration Options

### General Settings
- `library_root`: Absolute path to your music library.
- `recordings_root`: Absolute path to your recordings inbox.
- `auth_mode`: `auto`, `token`, `oauth`, or `key_secret`.

### Tagging & Numbering
- `tag_mode`: 
    - `replace`: (Default) Wipes all existing tags before writing.
    - `merge`: Keeps existing tags.
- `track_numbering`:
    - `numeric`: Sequential integers (1, 2, 3).
    - `original`: Discogs positions (A1, B1).
    - `per_side`: Resets count for each vinyl side.
- `disc_mapping`:
    - `physical`: Groups sides into discs (A/B=1, C/D=2).
    - `single`: Everything is Disc 1.
    - `per_side`: Each side is its own Disc.

### Naming & Organization
- `naming_pattern`: The template for your file paths. Default: `{artist}/{year} - {album}/{track_number} - {title}`

### Artwork & Metadata Files
- `image_handling`: `embed`, `save`, `both`, or `none`.
- `artwork_filename`: Name of the saved image file. Default: `folder.jpg`.
- `collect_all_artwork`: `true` to download all images from the release.
- `artwork_subdir`: Folder for additional images. Default: `Artwork`.
- `info_filename`: Name of the text summary file. Default: `release_info.txt`.

### Safety & Backups
- `backup_enabled`: `true` to copy files before tagging.
- `backup_dir`: Path where backups are stored.

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
