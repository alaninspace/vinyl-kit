# Feature Specification: VinylKit CLI Manager

**Feature Branch**: `001-vinylkit-cli-manager`  
**Created**: 2026-02-07  
**Status**: Implemented
**Input**: User description: "Build \"vinylkit\" — a cross-platform CLI tool for managing digitised vinyl record audio files using metadata from Discogs..."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initial Tagging of a Recorded Album (Priority: P1)

As a vinyl enthusiast, I want to tag a folder of freshly recorded audio files with full Discogs metadata so that my digital library is organized and searchable.

**Why this priority**: This is the core value proposition of the tool. Without the ability to tag files from Discogs, the tool serves no purpose.

**Independent Test**: Can be tested by providing a Discogs Release ID and a folder of untagged files, then verifying the files are tagged correctly.

**Acceptance Scenarios**:

1. **Given** a folder of untagged MP3 files and a valid Discogs Release ID, **When** I run the tag command, **Then** all files should be updated with artist, album, track titles, and vinyl-specific metadata (like side and position).
2. **Given** a release with multiple artists or credits, **When** I tag the files, **Then** all metadata should be correctly mapped to the appropriate tags in the audio file.

---

### User Story 2 - Interactive Search and Selection (Priority: P1)

As a user who doesn't know the exact Release ID, I want to search for an album by artist and title and pick the correct pressing from a list of results.

**Why this priority**: Users often won't have the Release ID handy and need an easy way to find the correct data source.

**Independent Test**: Can be tested by performing a search and selecting an item from the presented list, then verifying the correct release metadata is retrieved.

**Acceptance Scenarios**:

1. **Given** a search query for "Pink Floyd - Dark Side of the Moon", **When** I perform a search, **Then** I should see a list of releases including year, country, and format.
2. **Given** a list of search results, **When** I select one, **Then** the tool should fetch the full details for that specific release.

---

### User Story 3 - Safe Renaming and Reorganization (Priority: P2)

As a meticulous collector, I want to rename and move my files into a structured folder hierarchy based on their tags without risking data loss.

**Why this priority**: Organization is a key part of library management. Dry-run and safety features are critical when moving files.

**Independent Test**: Can be tested by running a rename operation in dry-run mode and verifying the output, then running it for real and verifying the file system changes.

**Acceptance Scenarios**:

1. **Given** a set of tagged files and a naming pattern like `{artist}/{album}/{track_number} - {title}`, **When** I run a dry-run rename, **Then** I should see a preview of the new paths without any actual moves occurring.
2. **Given** a rename operation, **When** the operation finishes, **Then** the original files should be in their new locations and no files should be deleted.

---

### User Story 4 - Artwork Management (Priority: P2)

As a user who wants a visually rich library, I want to embed album art into my files and optionally save them as separate image files.

**Why this priority**: Artwork is essential for modern music players and many users prefer having external files for higher quality or compatibility.

**Independent Test**: Can be tested by tagging an album with artwork enabled and verifying the presence of embedded images and local files (e.g., `folder.jpg`).

**Acceptance Scenarios**:

1. **Given** a release with multiple images, **When** I tag the album with "embed and save" enabled, **Then** the primary image should be embedded in the files and saved as `folder.jpg` in the folder.

---

### User Story 5 - Library Migration (Priority: P2)

As a user with an existing digital library, I want to migrate my files into the VinylKit structure while preserving my original files and tracking the changes.

**Why this priority**: Helps onboard users with large existing collections.

**Independent Test**: Can be tested by migrating a folder with a `[ID]` suffix, verifying the new structure is created, tags are cleaned/replaced, and a migration log is generated.

**Acceptance Scenarios**:

1. **Given** a source folder with subdirectories like `Artist - Title [123]`, **When** I run the migrate command, **Then** a new library structure should be created in the destination, files should be copied and tagged, and a `00-Migration-Results.txt` log should be created.
2. **Given** a folder without an ID, **When** I run migrate, **Then** the system should prompt for an ID and allow skipping.
3. **Given** a migration with `--delete`, **When** the operation for a folder succeeds, **Then** the source folder should be removed.

---

### Edge Cases

- **Sanitization**: How does the system handle artists like "AC/DC" or titles with `:` on Windows? (System MUST sanitize filenames for the target OS).
- **Rate Limiting**: What happens if the Discogs API limit is reached during a batch operation? (System MUST pause and retry with backoff).
- **Missing Side/Track Mapping**: What if the number of files doesn't match the tracklist on Discogs? (System MUST warn the user and require manual confirmation or skip).
- **Partial Tagging**: What if a file is already partially tagged? (System SHOULD have a setting to overwrite or skip).
- **Existing Destination Paths**: What if the destination path for a rename/move operation already contains files? (System MUST detect collisions and require explicit user confirmation before overwriting).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fetch metadata from Discogs API using Release ID or Search.
- **FR-002**: System MUST support Discogs Personal Access Token and OAuth 1.0a authentication.
- **FR-003**: System MUST write metadata to MP3 (ID3v2.4) and FLAC (Vorbis comments).
- **FR-004**: System MUST support customizable naming templates for file reorganization.
- **FR-005**: System MUST provide a mandatory dry-run mode or clear preview before writing changes.
- **FR-006**: System MUST scan folders and report on tag status, format, and audio properties.
- **FR-007**: System MUST support batch processing of multiple albums.
- **FR-008**: System MUST support configurable artwork handling (embed, save separate, or both).
- **FR-009**: System MUST sanitize filenames for cross-platform compatibility (Windows, macOS, Linux).
- **FR-010**: System MUST backup original files if configured.
- **FR-011**: System MUST NOT delete files; only move them.
- **FR-012**: System MUST store configuration in a platform-appropriate TOML file.
- **FR-013**: System MUST detect destination collisions and prompt for confirmation before overwriting existing files or directories.
- **FR-014**: System MUST support library migration from existing folders using `[ID]` name patterns.
- **FR-015**: System MUST generate a `00-Migration-Results.txt` log documenting all mapping changes.
- **FR-016**: System MUST support optional deletion of source files after successful migration.

## Scope Boundaries

### In Scope (Added Post-Launch)

- **Collection export**: Read-only download of a user's Discogs collection as CSV (`collection download`).
- **Search filters**: Filtered search by `--artist`, `--album`, `--format` in addition to free-text `--search`.
- **Merge tagging**: Preserve existing tags while adding Discogs metadata (`--merge` / `tag_mode merge`).
- **Track numbering & disc mapping**: Configurable strategies for vinyl-to-digital number conversion.
- **Metadata export**: Auto-generated `release_info.txt` per album folder.
- **Library Migration**: Command to batch-process existing libraries based on ID-labeled folders.

### Out of Scope

- Audio recording or digitization workflow.
- Audio fingerprinting or automatic identification (e.g., AcoustID).
- Bidirectional synchronization with Discogs collections/wantlists (read-only export is in scope).
- Graphical User Interface (GUI) or web-based interface.
- Support for proprietary/closed audio formats without open-source tagging libraries.

## Dependencies & Assumptions

### Dependencies
- **Discogs API**: The tool relies on the availability and stability of the Discogs API.
- **Tagging Libraries**: Relies on underlying libraries for writing ID3 and Vorbis tags.

### Assumptions
- **User Authentication**: Users are expected to have a Discogs account for API access.
- **File Integrity**: The tool assumes audio files are not corrupted and are writable by the current user.
- **Internet Connection**: A stable internet connection is required for metadata retrieval and OAuth login.

### Key Entities *(include if feature involves data)*

- **AudioFile**: Represents a physical audio file on disk. Attributes: path, format, current tags, bit depth, sample rate, duration.
- **DiscogsRelease**: Metadata retrieved from Discogs. Attributes: artist, title, tracklist, year, country, label, images, vinyl-specific info (side, matrix).
- **NamingTemplate**: A pattern used to generate file paths. Attributes: template string (e.g., `{artist} - {title}`).
- **Configuration**: User settings. Attributes: API credentials, default library path, naming patterns, backup settings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can search for and select a release in under 30 seconds.
- **SC-002**: 100% of supported tags (including vinyl-specific ones) are correctly written to audio files as verified by standard tag editors.
- **SC-003**: No files are lost or accidentally deleted during renaming or tagging operations.
- **SC-004**: Filenames generated on one OS (e.g., Linux) are valid and accessible if the library is moved to another OS (e.g., Windows).
- **SC-005**: The tool respects Discogs rate limits, ensuring no 429 errors occur during normal batch operations.
- **SC-006**: Zero accidental overwrites: 100% of destination collisions result in a user warning and require explicit confirmation.
- **SC-007**: Migration Traceability: Every migrated file is logged with its original and new paths in the migration results file.

## Future Enhancements (Low-Hanging Fruit)

### `vinylkit info` — Display Existing Tags
Read and display the current tags from a file or folder in a formatted table. The scanning/reading infrastructure already exists in `tagging.py`; this just needs a new Click command that presents the data instead of writing it. Useful for verifying tags without opening a separate editor.

### Wantlist Export
Same pattern as `collection download` but hitting the Discogs wantlist API endpoint. The HTTP client, CSV export logic, and pagination handling are already in place — this is essentially a second route on the same infrastructure.

### Undo Last Tag Operation
The backup system (`backup_enabled` / `backup_dir`) already copies files before tagging. A `vinylkit undo` command could restore from the most recent backup. The backup directory and file-copy logic exist; the missing piece is a manifest file recording what was backed up and where it came from.

### ID3v2.3 Output Option
Some older car stereos and portable players only support ID3v2.3. Mutagen supports writing v2.3 via the `v2_version` parameter on `save()`. A `id3_version` config key (`"2.3"` or `"2.4"`) would feed into a single parameter change in `tagging.py`.

### Scan Output Formats
Export `scan` results as CSV or JSON instead of only the Rich table. Useful for piping into other tools or generating reports. The scan data is already structured as `AudioFile` dataclasses — serialization would be straightforward.