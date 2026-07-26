# Changelog

All notable changes to VinylKit will be documented in this file.

## [v0.15.1] - 2026-07-26

### Added
- **Vinyl Position Overrides (`position_overrides`)**: Map non-standard vinyl side labels (`THIS`, `THAT`, `LOGO`, `INFO`) to standard vinyl side letters (`A`, `B`).
- **CLI Configuration Subcommands**:
  - `vinylkit config override set OLD NEW` (e.g. `vinylkit config override set THIS A`)
  - `vinylkit config override remove OLD`
  - `vinylkit config override list`
  - `vinylkit config set position_overrides "THIS:A,THAT:B"`
- Automated release notes generation in GitHub Actions release workflow (`release_vinylkit-cli.yml`).

### Fixed
- Fixed false positive collaboration detection in folder consolidation scripts when artist names contain `&` or `And` (e.g. `DJ Blatant & The Master Programmer`).

---

## [v0.15.0] - 2026-07-26

### Added
- **Discogs Artist Name Variation (ANV) Handling (`anv_handling`)**:
  - Options: `"none"` (default), `"prompt"`, `"primary"`.
  - Upfront ANV resolution during tagging to ensure 100% metadata consistency across audio tags (`ARTIST`, `ALBUMARTIST`, `ARTISTSORT`, `ALBUMARTISTSORT`), `release_info.txt`, and folder path generation (`{artist}`).
- **Interactive ANV Prompt (`anv_handling = "prompt"`)**: Displays a `rich` panel during batch/single tagging when ANVs are present on a release, letting users choose between Primary Artist Name and Release Variation.
- **CLI Flags**: `--anv-handling [none|prompt|primary]` and convenience alias `--use-primary-artist` / `--no-use-primary-artist`.

---

## [v0.14.3] - 2026-06-18

### Changed
- Refined automated GitHub Actions release workflow (`release_vinylkit-cli.yml`).
- Fixed package manager formula/manifest hash sync for Homebrew and Scoop.

---

## [v0.14.2] - 2026-06-17

### Added
- **Cross-Platform Standalone Distribution**: Standalone CLI builds using PyInstaller and PyApp.
- Package manager manifests for Homebrew Formula (`Formula/vinyl-kit.rb`) and Scoop (`scoop/vinylkit.json`).
- Cross-platform installation script and `vinylkit config reset` command.

---

## [v0.13.10] - 2026-06-11

### Added
- Documentation website (`docs_web`) and telemetry integration.
- System probe and health status endpoints for deployment monitoring.

---

## [v0.13.5] - 2026-05-18

### Added
- **Interactive Skip/Quit Options**: Enter `0` to skip an unsorted folder or `q` to terminate the batch session gracefully during interactive batch tagging.

---

## [v0.13.4] - 2026-05-15

### Added
- Documentation and examples for tagging network shares across Windows (UNC paths `\\server\share`) and macOS (mounted `/Volumes/` shares).

---

## [v0.13.0] - 2026-05-10

### Added
- **Interactive Batch Searching (`--batch --interactive`)**: Convert unsorted folder names into live Discogs search queries, preview matching release results, and tag/move files with a single keypress.

---

## [v0.12.0] - 2026-04-28

### Added
- Smart `full_title` track placeholder generation, automatically incorporating featuring artists and track-level artist credits when track artists differ from the release artist.

---

## [v0.11.4] - 2026-04-20

### Added
- Enhanced track title formatting and featuring artist string normalization.

---

## [v0.11.2] - 2026-04-15

### Changed
- Performance optimization for batch tagging using thread pool parallelization for audio file scanning and hash calculation.

---

## [v0.10.2] - 2026-04-01

### Added
- **`normalize_discogs_duplicates` Setting**: Automatically strip Discogs disambiguation suffixes (e.g. `(2)`, `(15)`) from artist, label, and company tags and folder names.
- **`--delete-source` Flag**: Automatically remove empty source directories after tagging and auto-moving audio files.

---

## [v0.9.2] - 2026-03-15

### Added
- Styled console error panels, status tables, and auth identity outputs powered by `rich` and `rich-click`.
- Rich-click integration and interactive examples across CLI help strings.

---

## [v0.8.0] - 2026-03-01

### Added
- Public CLI framework release.
- Core CLI commands: `vinylkit tag`, `vinylkit migrate`, `vinylkit auth`, `vinylkit collection`, `vinylkit config`, `vinylkit cache`.

---

## [v0.7.0] - 2026-02-28

### Added
- Two-phase file renaming and moving in `vinylkit tag` with transactional error handling and rollback.

---

## [v0.6.0] - 2026-02-25

### Added
- Dynamic progress bar and percentage tracking for `vinylkit migrate`.
- Cache management CLI commands (`vinylkit cache list`, `vinylkit cache clear`).

---

## [v0.5.0] - 2026-02-22

### Added
- Comprehensive 32-tag metadata engine (`mutagen`) with `skip_tags` configuration.
- Dual-sink structured logging framework powered by `loguru`.

---

## [v0.4.0] - 2026-02-20

### Added
- Discogs API rate-limit tracking and smart throttling with exponential backoff.

---

## [v0.3.0] - 2026-02-18

### Added
- Library migration feature (`vinylkit migrate`) with configurable target structure.

---

## [v0.2.0] - 2026-02-16

### Added
- File collision detection and user confirmation safety prompts for destructive operations.

---

## [v0.1.0] - 2026-02-15

### Added
- Initial project setup, Discogs OAuth 1.0a authentication client, and path template engine (`naming.py`).
