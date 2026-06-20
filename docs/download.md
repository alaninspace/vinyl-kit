# Download & Install VinylKit

[**Install**](#1-quick-one-line-script-recommended) &bull; [**Update**](#updating-vinylkit) &bull; [**Uninstall**](#uninstallation)

VinylKit can be installed in several different ways depending on your technical comfort level.

---

## 1. Quick One-Line Script (Recommended)

This is the fastest and most convenient method. The installer script automatically detects your operating system and CPU architecture, downloads the latest pre-compiled binary, installs it to a local folder, and configures your system `PATH`.

### macOS & Linux (Bash/Zsh)

Run the following command in your terminal:

```bash
curl -fsSL https://vinylkit.app/install.sh | bash
```

> [!NOTE]
> On macOS, the script will automatically bypass the Gatekeeper quarantine check for the downloaded binary, so you can run it immediately without seeing security prompt blockers.

### Windows (PowerShell)

Open PowerShell and run the following command:

```powershell
irm https://vinylkit.app/install.ps1 | iex
```

### Windows (Command Prompt / CMD)

Open CMD and run:

```cmd
curl -fsSL https://vinylkit.app/install.cmd -o install.cmd && install.cmd && del install.cmd
```

---

## 2. Direct Standalone Executables (PyInstaller)

If you prefer to download and configure your path manually, you can download the standalone executables directly. They contain the complete Python runtime and require zero dependencies.

| Operating System | Architecture | Archive Format | Download Link |
| :--- | :--- | :--- | :--- |
| **macOS** | Apple Silicon (M1/M2/M3) | `.zip` | [Download](https://github.com/alaninspace/vinyl-kit/releases/latest/download/vinylkit-macos-arm64.zip) |

| **Windows** | x64 (AMD64) | `.zip` | [Download](https://github.com/alaninspace/vinyl-kit/releases/latest/download/vinylkit-windows-amd64.zip) |
| **Linux** | x64 (AMD64) | `.tar.gz` | [Download](https://github.com/alaninspace/vinyl-kit/releases/latest/download/vinylkit-linux-amd64.tar.gz) |

### Manual Installation Steps:
1. Extract the downloaded archive.
2. Move the `vinylkit` (or `vinylkit.exe`) binary to a folder of your choice (e.g., `~/bin` or `C:\bin`).
3. Add that folder to your system `PATH` environment variable.

> [!WARNING]
> **Migrating from `uv`?** If you previously installed VinylKit using `uv tool install vinylkit`, your system `PATH` is currently pointing to the `uv` version. If you add this standalone executable to your `PATH` as well, they will conflict depending on which folder appears first. To migrate to the standalone executable, first run `uv tool uninstall vinylkit` to completely remove the old version.

> [!NOTE]
> **macOS Quarantine:** If you download the standalone binary directly via a web browser, macOS will flag it as quarantined. You can remove the quarantine flag by running:
> ```bash
> xattr -d com.apple.quarantine vinylkit
> ```

### Testing Without Modifying `PATH`
You do not have to add the executable to your `PATH` just to test it! You can run it directly by specifying its explicit path in your terminal. For example, if you extracted it to your current folder, run:
- **Windows (PowerShell):** `.\vinylkit.exe --help`
- **macOS / Linux:** Run `chmod +x vinylkit` first to make it executable, then run `./vinylkit --help`

By prefixing the command with `.\` or `./`, your terminal ignores your system `PATH` entirely and runs the exact file you extracted.

---

## 3. Standalone Launchers (PyApp)

PyApp provides extremely lightweight Rust-based bootstrappers. Rather than downloading a large 25MB+ binary, the launcher is under 1MB. Upon first execution, it fetches and caches the required Python runtime and VinylKit files.

*   [Download for macOS (Apple Silicon)](https://github.com/alaninspace/vinyl-kit/releases/latest/download/vinylkit-pyapp-macos-arm64)
*   [Download for macOS (Intel)](https://github.com/alaninspace/vinyl-kit/releases/latest/download/vinylkit-pyapp-macos-x86_64)
*   [Download for Windows (x64)](https://github.com/alaninspace/vinyl-kit/releases/latest/download/vinylkit-pyapp-windows-amd64.exe)
*   [Download for Linux (x64)](https://github.com/alaninspace/vinyl-kit/releases/latest/download/vinylkit-pyapp-linux-amd64)

> [!TIP]
> **macOS / Linux Standalone Launchers:** Just like PyInstaller binaries, PyApp launcher binaries require execution permissions. If downloaded directly:
> 1. Grant execution permissions: `chmod +x vinylkit-pyapp-linux-amd64` (or `vinylkit-pyapp-macos-arm64`).
> 2. On macOS, if downloaded via browser, bypass quarantine: `xattr -d com.apple.quarantine vinylkit-pyapp-macos-arm64`.

---

## 4. Package Managers

If you prefer to manage your CLI applications via standard package managers:

### macOS / Linux (Homebrew)

Install directly from our raw GitHub recipe:

```bash
brew install https://raw.githubusercontent.com/alaninspace/vinyl-kit/main/Formula/vinyl-kit.rb
```

### Windows (Scoop)

Install directly from our Scoop manifest:

```powershell
scoop install https://raw.githubusercontent.com/alaninspace/vinyl-kit/main/scoop/vinylkit.json
```

---

## 5. Developer Path (From Source / Git)

If you are a developer and already have the Python runtime and `uv` installed, you can build and run VinylKit directly:

```bash
# Install globally via uv
uv tool install git+https://github.com/alaninspace/vinyl-kit.git
```

To update an installation via `uv`:

```bash
uv tool install git+https://github.com/alaninspace/vinyl-kit.git --force --no-cache
```

---

## Updating VinylKit

When a new version is released, here is how you update your installation based on the method you chose:

### 1. One-Line Scripts
Simply re-run the installation command. The script will fetch the latest binary and safely overwrite your existing one without affecting your configuration:
- **macOS/Linux:** `curl -fsSL https://vinylkit.app/install.sh | bash`
- **Windows (PowerShell):** `irm https://vinylkit.app/install.ps1 | iex`

### 2. Standalone Executables & PyApp Launchers
Download the latest archive or launcher binary from the **[GitHub Releases Page](https://github.com/alaninspace/vinyl-kit/releases)**, extract it, and replace your existing executable file with the new one.

### 3. Package Managers
- **Homebrew:** Update by running a reinstall using the raw formula URL:
  ```bash
  brew reinstall https://raw.githubusercontent.com/alaninspace/vinyl-kit/main/Formula/vinyl-kit.rb
  ```
- **Scoop:** Scoop automatically resolves version updates from the manifest URL. Run:
  ```powershell
  scoop update vinylkit
  ```

### 4. Developer Path (uv)
Run the install command with `--force` and `--no-cache` to pull the latest version and rebuild:
```bash
uv tool install git+https://github.com/alaninspace/vinyl-kit.git --force --no-cache
```

> [!TIP]
> **Switching from `uv` to a standalone executable?** Don't forget to run `uv tool uninstall vinylkit` before configuring your new `PATH` to avoid command conflicts!

---

## Uninstallation

To completely remove VinylKit:

### Script / Direct Installs
Delete the `.vinylkit` directory from your home folder:
- **macOS/Linux:** `rm -rf ~/.vinylkit`
- **Windows:** Delete the `%USERPROFILE%\.vinylkit` folder.
*(You can also optionally clean up the `PATH` entries from your `.zshrc`/`.bashrc` or Windows environment variables).*

### Package Managers
- **Homebrew:** `brew uninstall vinyl-kit`
- **Scoop:** `scoop uninstall vinylkit`
- **UV:** `uv tool uninstall vinylkit`
