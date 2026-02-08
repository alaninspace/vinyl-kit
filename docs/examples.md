# VinylKit Usage Examples

This guide provides comprehensive examples of how to use VinylKit with various parameter combinations. All examples use real electronic music releases from the collection.

## 1. Direct Tagging (By Discogs ID)

When you have the ID from the vinyl spine or a Discogs search, this is the fastest method.

### Basic ID Tagging
Tags the files in the current folder.
```bash
# Example: Green Velvet - Flash (Remixes)
vinylkit tag --id 19983
```

### ID Tagging + Rename + Auto-Move
Tags the files and immediately moves them to your organized library.
```bash
# Example: The Prodigy - Wind It Up (Rewound)
vinylkit tag --id 53088 --rename --auto-move
```

---

## 2. Precision Searching (Filtered)

Highly recommended for common artists or finding specific pressings.

### Filter by Artist and Album
```bash
# Example: Faithless - Insomnia
vinylkit tag --artist "Faithless" --album "Insomnia"
```

### Filter with Multiple Formats
Finds the release on either Vinyl or CD.
```bash
# Example: The Chemical Brothers - Hey Boy Hey Girl
vinylkit tag --artist "The Chemical Brothers" --album "Hey Boy Hey Girl" --format "Vinyl, CD"
```

---

## 3. Global Search (Fragment Search)

Use this when you only have a piece of information or a Catalog Number.

### Searching by Catalog Number
Often the most accurate way to find a specific pressing.
```bash
# Example: Plastikman - Sheet One (Plus 8 Records)
vinylkit tag --search "PLUS8028"
```

### Searching by Artist and Label
```bash
# Example: Jeff Mills on Purpose Maker
vinylkit tag --search "Jeff Mills Purpose Maker"
```

---

## 4. Workflows & Scenarios

### The "Inbox" Workflow (Default Mode)
If you have `recordings_root` set in your config, you can run commands without paths.
```bash
# 1. See what's in your inbox
vinylkit scan

# 2. Tag and move the first folder found
vinylkit tag --artist "Underworld" --album "Born Slippy"
```

### The "Safety First" Preview
Always use `--dry-run` to see what tags will be written and where files will move.
```bash
# Example: Massive Attack - Unfinished Sympathy
vinylkit tag --id 1480380 --rename --dry-run
```

### Batch Processing
Tag multiple folders at once. You will be prompted for each one.
```bash
# Process all folders in a specific directory
vinylkit tag /path/to/batch/folder/* --rename
```

---

## 5. Configuration Examples

### Set up for Automated Moves
Bypass confirmation prompts for all future tagging.
```bash
vinylkit config set auto_move true
```

### Change Search Result Density
Show 10 results at a time instead of 5.
```bash
vinylkit config set search_page_size 10
```

### Custom Library Organization
Change how folders are nested.
```bash
# Example: Artist / Label / [Year] Title
vinylkit config set naming_pattern "{artist}/{label}/[{year}] {album}/{track_number} - {title}"
```

---

## 6. Advanced Overrides

### Manual Library Root Override
Move files to a different location than your default library.
```bash
# Example: Daft Punk - Homework
vinylkit tag --id 236605 --rename --library-root "E:\Archive\Techno"
```

### Merge Mode
Keep your existing comments or custom tags while updating from Discogs.
```bash
# Example: Satoshi Tomiie - Love In Traffic
vinylkit tag --id 28203 --merge
```

---

## 7. Collection Management

### Download Collection
Export your entire Discogs collection to a local CSV file.
```bash
vinylkit collection download
```
