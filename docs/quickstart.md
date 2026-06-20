# Quickstart: VinylKit CLI

## Installation

There are a few ways to install VinylKit. Pick the one that fits your setup:

### Option 1: Standalone Installer

To get VinylKit running without manually setting up Python or package managers:

* **macOS & Linux (Bash/Zsh):**
  ```bash
  curl -fsSL https://vinylkit.app/install.sh | bash
  ```
* **Windows (PowerShell):**
  ```powershell
  irm https://vinylkit.app/install.ps1 | iex
  ```

### Option 2: Python / Developer Tool (`uv`)

For developers and power users who already have Python and `uv` installed:

```bash
uv tool install git+https://github.com/alaninspace/vinyl-kit.git
```

> [!TIP]
> **Migrating from `uv` to a standalone executable?** If you already have VinylKit installed globally via `uv`, make sure to run `uv tool uninstall vinylkit` before installing the standalone version to avoid system `PATH` conflicts!

*For alternative installation options—including manual PyInstaller downloads, PyApp bootstrappers, Homebrew, and Scoop—see the full **[Download & Install Guide](download.md)**.*

---

## Setup & Configuration

VinylKit needs to know where your music library is, where you put your new recordings, and how to talk to Discogs.

### 1. Set your Library Location

This is where your tagged and organized music library will live.

**Bash:**

```bash
vinylkit config set library_root ~/Music/VinylLibrary
```

**PowerShell:**

```powershell
vinylkit config set library_root "D:\Music\VinylLibrary"
```

### 2. Set your Recordings Location (The "Inbox")

This is where you place your new vinyl recordings (e.g. `01.flac`, `02.flac`) before tagging them. Setting this lets you run commands without typing the folder path every time.

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

**Available Placeholders:** `{artist}`, `{album}`, `{year}`, `{id}`, `{track_number}`, `{title}`, `{label}`, `{catalogue_number}`, `{side}`, `{genre}`, `{style}`, `{country}`, and more. See the [Configuration Guide — `naming_pattern`](configuration.md#naming_pattern) for the full list.

**Examples:**

- **Standard Chronological (Default):** `Artist / Year - Album / Track - Title`

```bash
# Bash / PowerShell
vinylkit config set naming_pattern "{artist}/{year} - {album}/{track_number} - {title}"
```

- **Deep Parentheses:** `Artist / Album (Year) / Track - Title`

```bash
# Bash / PowerShell
vinylkit config set naming_pattern "{artist}/{album} ({year})/{track_number} - {title}"
```

- **Flat Album Folders:** `Year - Artist - Album / Track - Title` (One folder per album)

```bash
# Bash / PowerShell
vinylkit config set naming_pattern "{year} - {artist} - {album}/{track_number} - {title}"
```

- **Completely Flat:** Everything in one folder

```bash
# Bash / PowerShell
vinylkit config set naming_pattern "{year} - {id} - {artist} - {album} - {track_number} - {title}"
```

---

## Common Workflows

If you configure your `recordings_root`, tagging files becomes much simpler because you don't have to specify the path every time.

### Scenario: Tagging and Moving a New Recording

If you just finished recording an album and the files are in your default recordings folder:

```bash
# Bash / PowerShell

# 1. Scan to see the files in your Recordings folder
vinylkit scan

# 2. Tag, Create release_info.txt, and Rename/Move to library in one go
# (Example: Jeff Mills - Kat Moda EP)
vinylkit tag --id 165
```

### Scenario: Tagging a specific folder

To tag files outside your default recordings folder, specify the path in the command:

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

### Scenario: Batch tagging multiple releases

> [!IMPORTANT]
> **Configuration Requirement:** Batch tagging requires setting your `recordings_root` (see Step 2 under Setup & Configuration), because the command scans this directory for folders named with Discogs IDs.

Name your folders with the Discogs ID so VinylKit can pick it up automatically. Three formats are supported:

- Bracket suffix: `Album Name [12345]`
- Bare numeric: `12345`
- URL-style prefix (copy-paste from the Discogs URL): `12345-Artist-Album-Title`

Then tag them all at once:

```bash
# Bash / PowerShell

# Tag, rename, and move to library
vinylkit tag --batch --auto-move

# Tag and rename in place (don't move to library)
vinylkit tag --batch --no-move
```

---

## Available Commands

Here is what you can run:

- **`scan`** — View audio files and their tagging status.
- **`tag`** — Tag files using a Discogs Release ID or interactive search, with optional rename/move.
- **`rename`** — Move already-tagged files into your library structure (dry-run by default).
- **`migrate`** — Migrate an existing library to the new folder structure.
- **`auth`** — Manage Discogs authentication (login, identity).
- **`config`** — View and update persistent settings.
- **`cache`** — List and clear cached Discogs API responses.
- **`collection`** — Download your Discogs collection as CSV.

For full syntax, options, and search tips, see the **[User Guide — Command Reference](user-guide.md#3-command-reference)**.

---

## Next Steps

- **[User Guide](user-guide.md)** — In-depth command reference, tagging details, and workflows.
- **[Examples Guide](examples.md)** — Real-world scenarios and command combinations.
- **[Configuration Guide](configuration.md)** — Full list of all settings with defaults and examples.

## Where is my config?

Your settings and keys live in a standard config file on your system:

- **Windows**: `%LOCALAPPDATA%\vinylkit\vinylkit\config.toml`
- **macOS**: `~/Library/Application Support/vinylkit/config.toml`
- **Linux**: `~/.config/vinylkit/config.toml`

Running `uv tool install --force` **will not** delete or reset these files.
