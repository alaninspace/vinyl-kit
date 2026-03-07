# Configuration Guide: VinylKit

You can check the installed version at any time with:

```bash
# Bash / PowerShell
vinylkit --version
```

VinylKit settings are stored in a TOML file. You can view your current configuration (including version) at any time with:

```bash
# Bash / PowerShell
vinylkit config show
```

To update a setting, use the `set` command:

```bash
# Bash / PowerShell
vinylkit config set <KEY> <VALUE>
```

> [!TIP]
> Run `vinylkit config set -h` to see all valid keys and examples directly in your terminal.

---

## General Settings

### `library_root`

The final destination for your organized music library.

**Bash:**

- **Example:** `vinylkit config set library_root ~/Music/VinylLibrary`

**PowerShell:**

- **Example:** `vinylkit config set library_root "D:\Music\VinylLibrary"`

### `recordings_root`

The "Inbox" folder where you put fresh vinyl rips. If set, commands like `scan` and `tag` will default to this path if no other path is provided.

**Bash:**

- **Example:** `vinylkit config set recordings_root ~/Recordings/Vinyl`

**PowerShell:**

- **Example:** `vinylkit config set recordings_root "C:\Temp\RecordedVinyl"`

### `auto_move`

Automatically move files to your library after successful tagging and renaming without asking for confirmation. Works well with `--batch` for fully hands-free processing. When this config setting is `true`, the `--auto-move` CLI flag is not needed.

- **Default:** `false`
- **Example:** `vinylkit config set auto_move true`
- **With batch:** `vinylkit tag --batch --auto-move`
- **Rename only:** `vinylkit tag --batch --no-move` (tag and rename in place, skip library move)

### `--batch` (CLI flag)

Batch mode for the `tag` command. Iterates subfolders of the given path, extracts Discogs IDs from folder names (bracket suffix like `Album [12345]` or bare numeric like `67890`), and tags each folder automatically. Cannot be combined with `--id`, `--search`, `--artist`, `--album`, or `--format`.

- **Type:** Flag (no value)
- **Example:** `vinylkit tag --batch --auto-move`
- **With dry-run:** `vinylkit tag --batch --dry-run`

### `--no-move` (CLI flag)

Rename files in place using the naming pattern but skip moving them to the library root. Mutually exclusive with `--auto-move`. When used without `--batch`, creates a subfolder structure inside the source folder. When used with `--batch`, renames each subfolder to match the naming pattern.

- **Type:** Flag (no value)
- **Example:** `vinylkit tag --batch --no-move`
- **Single release:** `vinylkit tag --id 19983 --no-move`

---

## Metadata & Tagging

### `naming_pattern`

The template used to generate folder and file paths.

- **Default:** `{artist}/{year} - {album}/{track_number} - {title}`
- **Placeholders:** `{artist}`, `{album}`, `{year}`, `{id}` / `{discogs_id}`, `{track_number}`, `{title}`, `{label}`, `{catalogue_number}`, `{side}`, `{genre}`, `{style}`, `{country}`.
- **Example:** `vinylkit config set naming_pattern "{artist}/{year} - {album} [{label}]/{track_number} - {title}"`

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
- `original`: Always disc 1 (Discogs format_quantity support is not yet implemented).
- **Example:** `vinylkit config set disc_mapping single`

### `info_filename`

The name of the professional release information file generated in each album folder.

- **Default:** `release_info.txt`
- **Example:** `vinylkit config set info_filename "00_metadata.txt"`

### `skip_tags`

A comma-separated list of canonical tag names to exclude from being written to audio files. Useful for omitting metadata you don't want (e.g., Discogs-specific fields, genre, artwork embedding). See the [Tag Mapping Reference](tag-mapping.md) for the full list of canonical names.

- **Default:** (empty — all tags are written)
- **Example:** `vinylkit config set skip_tags "genre,style,discogs_notes"`
- **Clear:** `vinylkit config set skip_tags "none"`

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

**Bash:**

- **Example:** `vinylkit config set backup_dir ~/Backups/VinylKit`

**PowerShell:**

- **Example:** `vinylkit config set backup_dir "C:\Backups\VinylKit"`

---

## Search & Discovery

### `search_page_size`

Controls how many results are shown per page during interactive search.

- **Default:** `5`
- **Example:** `vinylkit config set search_page_size 10`

### `default_format`

The default media format filter(s) applied to all searches. Multiple formats can be provided as a comma-separated list. Set to `none` to disable filtering.

- **Default:** `Vinyl`
- **Example:** `vinylkit config set default_format "Vinyl, CD"`

---

## Cache

Discogs API responses are cached locally as JSON files in the platform cache directory. This avoids redundant API calls when you re-tag or re-process a release you've already fetched.

| Platform | Default Cache Path |
| --- | --- |
| **Windows** | `%LOCALAPPDATA%\vinylkit\vinylkit\Cache` |
| **macOS** | `~/Library/Caches/vinylkit` |
| **Linux** | `~/.cache/vinylkit` |

### `cache_enabled`

Controls whether Discogs API responses are cached locally.

- **Default:** `true`
- **Example:** `vinylkit config set cache_enabled false`

### `cache list`

Lists all cached releases with their Discogs ID, artist, album, and age.

- **Example:** `vinylkit cache list`

### `cache clear`

Deletes cached Discogs API responses. Prompts for confirmation by default (destructive operation).

- `--yes` / `-y`: Skip the confirmation prompt.
- `--id <INTEGER>`: Clear only the cached response for a single Discogs Release ID instead of all cached releases. Bypasses the confirmation prompt since it targets a single release.

**Examples:**

```bash
# Interactive confirmation (default)
vinylkit cache clear

# Skip confirmation
vinylkit cache clear --yes
vinylkit cache clear -y

# Clear a single release
vinylkit cache clear --id 19983

# Clear a single release without confirmation
vinylkit cache clear --id 53088
```

---

## Library Migration

These settings apply to the `vinylkit migrate` command.

### `delete_after_migration`

Automatically delete the source folders after a successful migration.

- **Default:** `false`
- **Example:** `vinylkit config set delete_after_migration true`

### `replace_artwork_on_migration`

Whether to replace existing embedded artwork in audio files during migration with fresh images from Discogs. Artwork *files* (e.g. `folder.jpg`) are always saved per the `image_handling` config regardless of this setting.

- **Default:** `true`
- **Example:** `vinylkit config set replace_artwork_on_migration false`

### `replace_tags_on_migration`

Whether to clear and re-write audio tags from Discogs metadata during migration. When `false`, audio files are copied/moved without any tag modifications. Discogs data is still fetched for path generation, and supplementary files (`release_info.txt`, artwork files) are still written.

- **Default:** `true`
- **Example:** `vinylkit config set replace_tags_on_migration false`

---

## Logging

VinylKit uses dual-sink logging: a clean console sink for user-facing messages and a detailed rotating file sink for diagnostics. Per-file operations (tagging, moving, artwork saving) are logged at `DEBUG` and only appear in the log file. Command-level summaries and release separators are logged at `INFO` and appear in the console.

### `log_level`

The minimum log level displayed in the console.

- **Default:** `INFO`
- **Allowed:** `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **Example:** `vinylkit config set log_level DEBUG`

### `log_to_file`

Enable or disable the rotating log file.

- **Default:** `true`
- **Example:** `vinylkit config set log_to_file false`

### `log_file`

Custom path for the log file. When not set, VinylKit uses the platform default provided by `platformdirs`:

| Platform | Default Path |
| --- | --- |
| **Windows** | `%LOCALAPPDATA%\vinylkit\vinylkit\Logs\vinylkit.log` |
| **macOS** | `~/Library/Logs/vinylkit/vinylkit.log` |
| **Linux** | `~/.local/state/vinylkit/log/vinylkit.log` |

**Bash:**

- **Example:** `vinylkit config set log_file ~/logs/vinylkit.log`

**PowerShell:**

- **Example:** `vinylkit config set log_file "D:\Logs\vinylkit.log"`

### `log_rotation`

Controls when the log file is rotated. Accepts size-based (e.g. `"5 MB"`, `"100 MB"`) or time-based (e.g. `"1 day"`, `"1 week"`) specifications.

- **Default:** `5 MB`
- **Example:** `vinylkit config set log_rotation "10 MB"`

### `log_retention`

Number of rotated log files to keep before the oldest is deleted.

- **Default:** `5`
- **Example:** `vinylkit config set log_retention 3`

---

## Authentication

See the [Authentication Guide](auth.md) for a detailed walkthrough of these settings.

### `auth_mode`

Controls which authentication method VinylKit uses.

- **Default:** `auto`
- **Allowed:** `auto`, `token`, `oauth`, `key_secret`, `none`
- **Example:** `vinylkit config set auth_mode token`

### `consumer_key` / `consumer_secret`

Discogs Developer Application credentials. Required for OAuth login.

- **Example:** `vinylkit config set consumer_key "YOUR_KEY"`

### `discogs_token`

Personal access token from Discogs. The simplest auth method for most users.

- **Example:** `vinylkit config set discogs_token "YOUR_TOKEN"`

### `discogs_secret`

OAuth token secret, automatically set by `vinylkit auth login`. Can also be set manually when migrating credentials from another machine.

- **Example:** `vinylkit config set discogs_secret "YOUR_SECRET"`
