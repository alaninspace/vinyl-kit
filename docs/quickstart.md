# Quickstart: VinylKit CLI

## Installation

### From Source (For Developers)
Ensure you have `uv` installed. From the project root, run:

```bash
# Bash / PowerShell
uv tool install . --force
```

### From Git (For Users)
Users can install VinylKit directly from the repository:

```bash
# Bash / PowerShell
uv tool install git+https://github.com/alaninspace/vinyl-man.git
```

### Updating VinylKit
If you pull new changes or modify the code yourself, simply run the install command again with the `--force` and `--no-cache` flags. This ensures `uv` rebuilds the tool from your latest local source without affecting your saved settings.

```bash
# Bash / PowerShell
uv tool install . --force --no-cache
```

---

## Setup & Configuration

VinylKit needs to know where your music library is, where you put your new recordings, and how to talk to Discogs.

### 1. Set your Library Location
This is the final destination for your tagged and organized music.

**Bash:**
```bash
vinylkit config set library_root ~/Music/VinylLibrary
```

**PowerShell:**
```powershell
vinylkit config set library_root "D:\Music\VinylLibrary"
```

### 2. Set your Recordings Location (The "Inbox")
This is where you drop your fresh vinyl recordings (e.g. `01.flac`, `02.flac`) before tagging them. Setting this allows you to run commands without typing the path every time.

**Bash:**
```bash
vinylkit config set recordings_root ~/Recordings/Vinyl
```

**PowerShell:**
```powershell
vinylkit config set recordings_root "C:\Temp\RecordedVinyl"
```

### 3. Authenticate with Discogs
See the [Authentication Guide](auth.md) for detailed steps.

**Quick Start (Personal Access Token):**
```bash
# Bash / PowerShell
vinylkit config set discogs_token "YOUR_TOKEN"
```

> [!TIP]
> For a full list of all settings (backups, custom filenames, tagging modes), see the **[Configuration Guide](configuration.md)**.

### 4. Advanced Artwork Collection
By default, VinylKit only downloads the primary cover. You can enable full collection:

```bash
# Bash / PowerShell
# Download all images from the release
vinylkit config set collect_all_artwork true

# Customize the artwork subdirectory name
vinylkit config set artwork_subdir "Scans"
```

### 5. Folder Structure & Naming
You can control exactly how your library is organized and how deep the folders are by changing the `naming_pattern`.

**Available Placeholders:**
- `{artist}`, `{album}`, `{year}`
- `{id}` (Discogs Release ID), `{discogs_id}`
- `{track_number}`, `{title}`
- `{label}`, `{catalogue_number}`, `{side}`
- `{genre}`, `{style}`, `{country}`

**Examples:**

*   **Standard Chronological (Default):** `Artist / Year - Album / Track - Title`
    ```bash
    # Bash / PowerShell
    vinylkit config set naming_pattern "{artist}/{year} - {album}/{track_number} - {title}"
    ```

*   **Deep Parentheses:** `Artist / Album (Year) / Track - Title`
    ```bash
    # Bash / PowerShell
    vinylkit config set naming_pattern "{artist}/{album} ({year})/{track_number} - {title}"
    ```

*   **Flat Album Folders:** `Year - Artist - Album / Track - Title` (One folder per album)
    ```bash
    # Bash / PowerShell
    vinylkit config set naming_pattern "{year} - {artist} - {album}/{track_number} - {title}"
    ```

*   **Completely Flat:** Everything in one folder
    ```bash
    # Bash / PowerShell
    vinylkit config set naming_pattern "{year} - {id} - {artist} - {album} - {track_number} - {title}"
    ```

---

## Example Scenarios (The Easy Way)

If you have configured your `recordings_root`, your daily workflow becomes much simpler.

### Scenario: Tagging and Moving a New Recording
You just finished recording an album and the files are in your recordings folder.

```bash
# Bash / PowerShell

# 1. Scan to see the files in your Recordings folder
vinylkit scan

# 2. Tag, Create release_info.txt, and Rename/Move to library in one go
# (Example: Jeff Mills - Kat Moda EP)
vinylkit tag --id 165
```

### Scenario: Overriding the defaults
If you want to tag files in a *specific* folder instead of your default recordings folder:

**Bash:**
```bash
# Explicit path provided: --rename is NOT automatic in this workflow, must be added
# (Example: Krafty Kuts - Lost Plates E.P.)
vinylkit tag ~/Downloads/vinyl-rip --id 56903 --rename
```

**PowerShell:**
```powershell
# Explicit path provided: --rename is NOT automatic in this workflow, must be added
# (Example: Krafty Kuts - Lost Plates E.P.)
vinylkit tag "C:\Some\Other\Folder" --id 56903 --rename
```

---

## Available Commands

VinylKit provides the following commands:

- **`scan`** — View audio files and their tagging status.
- **`tag`** — Tag files using a Discogs Release ID or interactive search, with optional rename/move.
- **`rename`** — Move already-tagged files into your library structure (dry-run by default).
- **`auth`** — Manage Discogs authentication (login, identity).
- **`config`** — View and update persistent settings.
- **`collection`** — Download your Discogs collection as CSV.

For full syntax, options, and search tips, see the **[User Guide — Command Reference](user-guide.md#3-command-reference)**.

---

## Next Steps

- **[User Guide](user-guide.md)** — In-depth command reference, tagging details, and workflows.
- **[Examples Guide](examples.md)** — Real-world scenarios and command combinations.
- **[Configuration Guide](configuration.md)** — Full list of all settings with defaults and examples.

## Where is my config?
Your settings and keys are stored in a persistent location:
- **Windows**: `%LOCALAPPDATA%\vinylkit\config.toml`
- **macOS/Linux**: `~/.config/vinylkit/config.toml`

Running `uv tool install --force` **will not** delete or reset these files.
