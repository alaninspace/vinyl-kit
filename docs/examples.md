# VinylKit Usage Examples

This guide provides comprehensive examples of how to use VinylKit with various parameter combinations. All examples use real electronic music releases from the collection.

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

### Batch Processing
Tag multiple folders at once. You will be prompted for each one.

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

---

## 5. Configuration Examples

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
```

---

## 6. Advanced Overrides

### Manual Library Root Override
Move files to a different location than your default library.

**Bash:**
```bash
# Example: Daft Punk - Homework
vinylkit tag --id 236605 --rename --library-root ~/Archive/Techno
```

**PowerShell:**
```powershell
# Example: Daft Punk - Homework
vinylkit tag --id 236605 --rename --library-root "E:\Archive\Techno"
```

### Merge Mode
Keep your existing comments or custom tags while updating from Discogs.
```bash
# Bash / PowerShell
# Example: Satoshi Tomiie - Love In Traffic
vinylkit tag --id 28203 --merge
```

---

## 7. Collection Management

### Download Collection
Export your entire Discogs collection to a local CSV file.
```bash
# Bash / PowerShell
vinylkit collection download
```

---

## 8. Library Migration

Move an entire existing library into the VinylKit structure.

### Basic Library Migration
Processes all folders in the source, extracting IDs from `[ID]` suffixes.

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

---

## 9. Cache Management

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
