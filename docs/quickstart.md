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
uv tool install . --force --no-cache
```

---

## Setup & Configuration

VinylKit needs to know where your music library is, where you put your new recordings, and how to talk to Discogs.

### 1. Set your Library Location
This is the final destination for your tagged and organized music.

```powershell
vinylkit config set library_root "D:\Music\VinylLibrary"
```

### 2. Set your Recordings Location (The "Inbox")
This is where you drop your fresh vinyl recordings (e.g. `01.flac`, `02.flac`) before tagging them. Setting this allows you to run commands without typing the path every time.

```powershell
vinylkit config set recordings_root "C:\Temp\RecordedVinyl"
```

### 3. Authenticate with Discogs
See the [Authentication Guide](auth.md) for detailed steps.

**Quick Start (Personal Access Token):**
```powershell
vinylkit config set discogs_token "YOUR_TOKEN"
```

---

## Example Scenarios (The Easy Way)

If you have configured your `recordings_root`, your daily workflow becomes much simpler.

### Scenario: Tagging and Moving a New Recording
You just finished recording an album and the files are in `C:\Temp\RecordedVinyl`.

**PowerShell:**
```powershell
# 1. Scan to see the files in your Recordings folder
vinylkit scan

# 2. Tag, Create release_info.txt, and Rename/Move to library in one go
# (When no path is given, it uses recordings_root and defaults to --rename)
vinylkit tag --id 249504
```

### Scenario: Overriding the defaults
If you want to tag files in a *specific* folder instead of your default recordings folder:

**PowerShell:**
```powershell
# Explicit path provided: --rename is NOT automatic, must be added
vinylkit tag "C:\Some\Other\Folder" --id 123456 --rename
```

---

## Basic Usage Reference

### 1. Scan
See what's in a folder and its current tagging status:
```bash
# Scans recordings_root if set, else library_root
vinylkit scan

# Or scan a specific folder
vinylkit scan "C:\Temp\ManualFolder"
```

### 2. Tag and Organize (ID-based)
```bash
# Simplest (uses recordings_root + auto-rename)
vinylkit tag --id 249504

# Manual path (requires --rename flag)
vinylkit tag "C:\Path\To\Album" --id 249504 --rename
```

### 3. Interactive Search
```bash
vinylkit tag --search "Pink Floyd Dark Side"
```

---

## Where is my config?
Your settings and keys are stored in a persistent location:
- **Windows**: `%LOCALAPPDATA%\vinylkit\config.toml`
- **macOS/Linux**: `~/.config/vinylkit/config.toml`

Running `uv tool install --force` **will not** delete or reset these files.