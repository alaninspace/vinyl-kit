# Configuration Guide: VinylKit

VinylKit settings are stored in a TOML file. You can view your current configuration at any time with:

```bash
vinylkit config show
```

To update a setting, use the `set` command:
```bash
vinylkit config set <KEY> <VALUE>
```

---

## General Settings

### `library_root`
The final destination for your organized music library.
- **Example:** `vinylkit config set library_root "D:\Music\VinylLibrary"`

### `recordings_root`
The "Inbox" folder where you put fresh vinyl rips. If set, commands like `scan` and `tag` will default to this path if no other path is provided.
- **Example:** `vinylkit config set recordings_root "C:\Temp\RecordedVinyl"`

---

## Metadata & Tagging

### `naming_pattern`
The template used to generate folder and file paths.
- **Default:** `{artist}/{year} - {album}/{track_number} - {title}`
- **Placeholders:** `{artist}`, `{album}`, `{year}`, `{id}`, `{track_number}`, `{title}`, `{label}`, `{catalogue_number}`, `{side}`, `{genre}`, `{style}`, `{country}`.
- **Example:** `vinylkit config set naming_pattern "{artist}/{album} ({year})/{track_number} - {title}"`

### `tag_mode`
Controls how VinylKit writes metadata to files.
- `replace`: (Default) Clears all existing tags and writes fresh data from Discogs.
- `merge`: Preserves existing tags and only adds/updates the fields provided by Discogs.
- **Example:** `vinylkit config set tag_mode merge`

### `track_numbering`
Controls how track numbers are written to files. Essential for software like Roon.
- `numeric`: (Default) Converts vinyl positions (A1, B1) to sequential numbers (1, 2, 3...). **Recommended for Roon.**
- `original`: Keeps the original Discogs position (e.g., "A1").
- `per_side`: Resets the count for each side (A1->1, B1->1). Best used with `disc_mapping per_side`.
- **Example:** `vinylkit config set track_numbering original`

### `disc_mapping`
Controls how vinyl sides are mapped to the `DISCNUMBER` tag.
- `physical`: (Default) Intelligently groups sides. Pairs of sides (A/B, C/D) are mapped to Discs 1, 2, etc. Also respects numeric prefixes (e.g., "1A" maps to Disc 1). **Best for multi-LP sets.**
- `single`: All tracks are on Disc 1.
- `per_side`: Each vinyl side is treated as a separate disc (Side A=1, B=2...).
- `original`: Uses Discogs physical count if available.
- **Example:** `vinylkit config set disc_mapping single`

### `info_filename`
The name of the professional release information file generated in each album folder.
- **Default:** `release_info.txt`
- **Example:** `vinylkit config set info_filename "00_metadata.txt"`

---

## Artwork Management

### `image_handling`
Controls where the primary album cover is placed.
- `both`: (Default) Embeds the image in the audio files AND saves it as a file.
- `embed`: Only embeds the image inside the audio files.
- `save`: Only saves the image as a standalone file.
- `none`: Disables artwork processing.
- **Example:** `vinylkit config set image_handling embed`

### `artwork_filename`
The filename used for the primary cover image.
- **Default:** `folder.jpg`
- **Example:** `vinylkit config set artwork_filename "cover.jpg"`

### `collect_all_artwork`
Whether to download all images associated with a Discogs release.
- `true`: Download all images (primary + secondary).
- `false`: (Default) Only download the primary cover.
- **Example:** `vinylkit config set collect_all_artwork true`

### `artwork_subdir`
The name of the subdirectory where secondary images are stored if `collect_all_artwork` is enabled.
- **Default:** `Artwork`
- **Example:** `vinylkit config set artwork_subdir "Scans"`

---

## Safety & Backups

### `backup_enabled`
Automatically creates a copy of your audio files before modification.
- `true`: Enable backups.
- `false`: (Default) Disable backups.
- **Example:** `vinylkit config set backup_enabled true`

### `backup_dir`
The directory where backups are stored. Required if `backup_enabled` is true.
- **Example:** `vinylkit config set backup_dir "C:\Backups\VinylKit"`

---

## Authentication

See the [Authentication Guide](auth.md) for a detailed walkthrough of these settings.

- `auth_mode`: `auto` (Default), `token`, `oauth`, `key_secret`.
- `consumer_key` / `consumer_secret`: Discogs Developer Application credentials.
- `discogs_token` / `discogs_secret`: User-specific authentication tokens.
