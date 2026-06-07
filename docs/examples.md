# VinylKit Usage Examples

This guide provides comprehensive examples of how to use VinylKit with various parameter combinations. All examples use real electronic music releases from the collection.

## Getting Help

Every command supports `-h` to display detailed help with examples and option groups.

```bash
# Bash / PowerShell

# Show the full command overview with quick-start steps
vinylkit -h

# Show tag options grouped by purpose, with examples
vinylkit tag -h

# List all valid configuration keys
vinylkit config set -h
```

---

## 1. Direct Tagging (By Discogs ID)

When you have the ID from the vinyl spine or a Discogs search, this is the fastest method.

### Basic ID Tagging

Tags the files in the current folder.

```bash
# Bash / PowerShell
# Example: Green Velvet - Flash (Remixes)
vinylkit tag --id 19983
```

### ID Tagging + Rename + Auto-Move

Tags the files and immediately moves them to your organized library.

```bash
# Bash / PowerShell
# Example: The Prodigy - Wind It Up (Rewound)
vinylkit tag --id 53088 --rename --auto-move
```

### ID Tagging + Rename + Auto-Move + Delete Source

Tags, moves to library, and removes the now-empty source folder.

```bash
# Bash / PowerShell
# Example: The Prodigy - Wind It Up (Rewound)
vinylkit tag --id 53088 --rename --auto-move --delete-source
```

### Multi-ID Workflow (CSV IDs + Named Folders)

Process several albums in one command. Rename each source folder to its Discogs
ID, then pass a comma-separated list of IDs. VinylKit performs a direct path
lookup (`{library-root}/{id}/`) for each ID — no directory scan.

```bash
# Bash / PowerShell
# Folders: D:\Music\DJ\Vinyl\391682\  and  D:\Music\DJ\Vinyl\30038\
vinylkit tag --id 391682,30038 --library-root "D:\Music\DJ\Vinyl" --rename --auto-move --delete-source
```

### Multi-ID with a Separate Source Folder

When your unprocessed files live outside the library root, pass the source
folder as a single PATH. VinylKit looks for `{PATH}/{id}/` for each ID, tags
the files, and moves them to `--library-root`.

```bash
# Bash / PowerShell
# Source folders: D:\Music\DJ\Vinyl\#Unsorted\182338\  and  ...\74044\
# Destination:    D:\Music\DJ\Vinyl\
vinylkit tag "D:\Music\DJ\Vinyl\#Unsorted" --id 182338,74044 --library-root "D:\Music\DJ\Vinyl" --rename --auto-move --delete-source
```

---

## 2. Precision Searching (Filtered)

Highly recommended for common artists or finding specific pressings.

### Filter by Artist and Album

```bash
# Bash / PowerShell
# Example: Faithless - Insomnia
vinylkit tag --artist "Faithless" --album "Insomnia"
```

### Filter with Multiple Formats

Finds the release on either Vinyl or CD.

```bash
# Bash / PowerShell
# Example: The Chemical Brothers - Hey Boy Hey Girl
vinylkit tag --artist "The Chemical Brothers" --album "Hey Boy Hey Girl" --format "Vinyl, CD"
```

---

## 3. Global Search (Fragment Search)

Use this when you only have a piece of information or a Catalog Number.

### Searching by Catalog Number

Often the most accurate way to find a specific pressing.

```bash
# Bash / PowerShell
# Example: Plastikman - Sheet One (Plus 8 Records)
vinylkit tag --search "PLUS8028"
```

### Searching by Artist and Label

```bash
# Bash / PowerShell
# Example: Jeff Mills on Purpose Maker
vinylkit tag --search "Jeff Mills Purpose Maker"
```

---

## 4. Workflows & Scenarios

### The "Inbox" Workflow (Default Mode)

If you have `recordings_root` set in your config, you can run commands without paths.

```bash
# Bash / PowerShell

# 1. See what's in your inbox
vinylkit scan

# 2. Tag and move the first folder found
vinylkit tag --artist "Underworld" --album "Born Slippy"
```

### The "Safety First" Preview

Always use `--dry-run` to see what tags will be written and where files will move.

```bash
# Bash / PowerShell
# Example: Massive Attack - Unfinished Sympathy
vinylkit tag --id 1480380 --rename --dry-run
```

### Batch Mode

Automatically tag all subfolders in your recordings inbox. Each folder
name must contain a Discogs ID in one of three formats: bracket suffix
(e.g. `Artist - Album [12345]`), bare number (e.g. `12345`), or
URL-style prefix (e.g. `12345-Artist-Album`, matching the Discogs release URL).

```bash
# Bash / PowerShell

# Tag + rename in place (no move to library)
vinylkit tag --batch --no-move

# Process all subfolders in recordings_root (uses config default)
vinylkit tag --batch --auto-move

# Process subfolders in a specific directory
vinylkit tag /path/to/inbox --batch --auto-move

# Preview batch processing without writing anything
vinylkit tag --batch --dry-run
```

### Manual Batch (Per-Folder Prompts)

Tag multiple explicit folders at once. You will be prompted for each one.

**Bash:**

```bash
# Process all folders in a specific directory
vinylkit tag /path/to/batch/folder/* --rename
```

**PowerShell:**

```powershell
# Process all folders in a specific directory
vinylkit tag C:\Path\To\Batch\Folder\* --rename
```

### Interactive Batch Searching

If you have a folder full of unsorted music (e.g. from friends or unlabelled downloads) where the folders are named with Artist and Title (e.g., `Desired_State-Desired_State_EP-(STRAT_8)`), you can use `--interactive` with `--batch` to rapidly process them.

This command will iterate through every folder. It automatically converts the folder name into a search query (e.g., `Desired State Desired State EP STRAT 8`), and shows you the Discogs results table. You just type `1` to confirm, and VinylKit will instantly tag, rename, move to your library, and delete the source folder, before moving on to the next folder.

**Windows (Mapped Network Drive Example):**
```powershell
vinylkit tag "D:\Music\DJ\#Unsorted\Vinyl" --batch --interactive --library-root "D:\Music\DJ\Vinyl" --rename --auto-move --delete-source
```

**macOS (Mounted Network Share SMB Example):**
> [!NOTE]
> Command-line tools cannot directly resolve `smb://` paths. You must mount the network share first (e.g., via Finder using `Cmd + K` to connect to `smb://DiskStation/HomeMedia`), which will make it accessible under `/Volumes/`.

```bash
vinylkit tag "/Volumes/HomeMedia/Music/DJ/#Unsorted/Vinyl" --batch --interactive --library-root "/Volumes/HomeMedia/Music/DJ/Vinyl" --rename --auto-move --delete-source
```

### Skip Artwork Embedding

Tag files without downloading or embedding any artwork.

```bash
# Bash / PowerShell
# Example: Aphex Twin - Selected Ambient Works 85-92
vinylkit tag --id 31 --no-artwork
```

### Tag Without Moving

Tag files in place without moving them to the library, even when using `recordings_root`.

```bash
# Bash / PowerShell
# Example: Orbital - Chime
vinylkit tag --id 62122 --no-rename
```

---

## 5. Rename & Organize (Without Re-tagging)

### Dry-run Rename Preview

Preview how already-tagged files would be organized (default is dry-run).

```bash
# Bash / PowerShell
# Example: Leftfield - Leftism
vinylkit rename /path/to/album --id 6108
```

### Commit the Rename

Actually move the files after previewing.

```bash
# Bash / PowerShell
# Example: Leftfield - Leftism
vinylkit rename /path/to/album --id 6108 --commit
```

---

## 6. Configuration Examples

### Set up for Automated Moves

Bypass confirmation prompts for all future tagging.

```bash
# Bash / PowerShell
vinylkit config set auto_move true
```

### Change Search Result Density

Show 10 results at a time instead of 5.

```bash
# Bash / PowerShell
vinylkit config set search_page_size 10
```

### Custom Library Organization

Change how folders are nested.

```bash
# Bash / PowerShell

# Example: Artist / Label / [Year] Title
vinylkit config set naming_pattern "{artist}/{label}/[{year}] {album}/{track_number} - {title}"

# Example: with label in square brackets
vinylkit config set naming_pattern "{artist}/{year} - {album} [{label}]/{track_number} - {title}"

# Example: with track artist (useful for compilations like "Various Artists")
vinylkit config set naming_pattern "{artist}/{year} - {album} [{label}]/{track_number} - {track_artist} - {title}"
```

### Normalise Discogs Duplicates

Enable or disable the automatic removal of Discogs disambiguation suffixes (like `(2)`).

```bash
# Bash / PowerShell

# Keep raw Discogs names (e.g. "What's In It For Me Music (2)")
vinylkit config set normalize_discogs_duplicates false

# Use clensed names (e.g. "What's In It For Me Music") - [DEFAULT]
vinylkit config set normalize_discogs_duplicates true
```

---

### View Current Configuration

Display the VinylKit version, all settings, and the config file path.

```bash
# Bash / PowerShell
vinylkit config show
```

### Check Version

Display the installed VinylKit version.

```bash
# Bash / PowerShell
vinylkit --version
```

---

## 7. Advanced Overrides

### Manual Library Root Override

Move files to a different location than your default library. Use `--auto-move` to skip the confirmation prompt.

**Bash:**

```bash
# Example: Daft Punk - Homework
vinylkit tag --id 236605 --rename --auto-move --library-root ~/Archive/Techno
```

**PowerShell:**

```powershell
# Example: Daft Punk - Homework
vinylkit tag --id 236605 --rename --auto-move --library-root "E:\Archive\Techno"
```

### Merge Mode

Keep your existing comments or custom tags while updating from Discogs.

```bash
# Bash / PowerShell
# Example: Satoshi Tomiie - Love In Traffic
vinylkit tag --id 28203 --merge
```

---

## 8. Authentication

### Check Current Identity

Display the authenticated Discogs user.

```bash
# Bash / PowerShell
vinylkit auth identity
```

---

## 9. Collection Management

### Download Collection

Export your entire Discogs collection to a local CSV file.

```bash
# Bash / PowerShell
vinylkit collection download
```

---

## 10. Library Migration

Move an entire existing library into the VinylKit structure.

### Basic Library Migration

Processes all folders in the source, extracting IDs from folder names (`Album [12345]`, bare `12345`, or `12345-Artist-Title`).

**Bash:**

```bash
# Example: Migrating a folder containing "Jondi & Spesh - Mysteries [49135]"
vinylkit migrate ~/Music/Source ~/Music/Organized
```

**PowerShell:**

```powershell
# Example: Migrating a folder containing "Jondi & Spesh - Mysteries [49135]"
vinylkit migrate "C:\Music\Source" "C:\Music\Organized"
```

### Migration with Clean-up

Migrate and delete original files once successfully copied and tagged.

**Bash:**

```bash
# Example: Migrating "Peace Division - Droppin' Deep EP [33511]"
vinylkit migrate ~/Music/Old ~/Music/New --delete
```

**PowerShell:**

```powershell
# Example: Migrating "Peace Division - Droppin' Deep EP [33511]"
vinylkit migrate "C:\Music\Old" "C:\Music\New" --delete
```

### Migrate Specific IDs

Only process folders that match specific Discogs Release IDs.

**Bash:**

```bash
# Example: Only migrate IDs 49135 and 37623
vinylkit migrate ~/Music/Source ~/Music/Organized --id "49135,37623"
```

**PowerShell:**

```powershell
# Example: Only migrate IDs 49135 and 37623
vinylkit migrate "C:\Music\Source" "C:\Music\Organized" --id "49135,37623"
```

### Dry-run Migration

Preview the entire migration process, including file mapping and naming, without touching any files.

**Bash:**

```bash
# Example: Preview migration for "Peace Division [33511]"
vinylkit migrate ~/Music/Old ~/Music/New --dry-run
```

**PowerShell:**

```powershell
# Example: Preview migration for "Peace Division [33511]"
vinylkit migrate "C:\Music\Old" "C:\Music\New" --dry-run
```

### Replace Artwork and Tags During Migration

Force fresh artwork and tags from Discogs, even if the files already have metadata.

```bash
# Bash / PowerShell
vinylkit migrate ~/Music/Old ~/Music/New --replace-artwork --replace-tags
```

---

## 11. Cache Management

### List Cached Releases

See what Discogs API responses are stored locally.

```bash
# Bash / PowerShell
vinylkit cache list
```

### Clear All Cached Releases (Interactive)

Delete all cached API responses. You will be asked to confirm.

```bash
# Bash / PowerShell
vinylkit cache clear
```

### Clear All Cached Releases (Skip Confirmation)

Use `--yes` (or `-y`) to skip the confirmation prompt.

```bash
# Bash / PowerShell
vinylkit cache clear --yes
vinylkit cache clear -y
```

### Clear a Single Cached Release

Remove the cached response for a specific Discogs Release ID using `--id`.

```bash
# Bash / PowerShell
# Example: Clear cached data for Green Velvet - Flash (Remixes)
vinylkit cache clear --id 19983
```

### Disable Caching

Turn off API response caching entirely.

```bash
# Bash / PowerShell
vinylkit config set cache_enabled false
```
