# Data Model: VinylKit CLI Manager

## Core Entities

### DiscogsRelease
Represents metadata fetched from the Discogs API.
- **id**: int (Primary Key from Discogs)
- **artists**: list[str]
- **title**: str
- **year**: int | None
- **country**: str | None
- **label**: str | None
- **catno**: str | None
- **format**: str (e.g., "LP", "7"", "12"")
- **tracklist**: list[TrackInfo]
- **images**: list[ImageInfo]

### TrackInfo
- **position**: str (e.g., "A1", "B2")
- **title**: str
- **artists**: list[str] | None
- **side**: str | None (Extracted from position, e.g., "A")

### AudioFile
Represents a physical file on the user's disk.
- **path**: pathlib.Path
- **extension**: str (mp3, flac)
- **tag_status**: enum (UNTAGGED, PARTIAL, TAGGED)
- **properties**: dict (sample_rate, bit_depth, duration)

### AppConfig
User settings stored in TOML.
- **discogs_token**: str | None
- **discogs_secret**: str | None (for OAuth)
- **library_root**: pathlib.Path
- **naming_pattern**: str
- **image_handling**: enum (EMBED, SAVE, BOTH, NONE)
- **backup_enabled**: bool
- **backup_dir**: pathlib.Path | None

## State Transitions

### Tagging Flow
1. **Unidentified**: Audio files in a folder.
2. **Matched**: Files mapped to a `DiscogsRelease`.
3. **Previewed**: User sees changes via dry-run.
4. **Tagged**: Metadata written to files; status updated to `TAGGED`.
5. **Organized**: Files moved to final location based on `NamingTemplate`.

## Validation Rules
- **Filenames**: Must not contain `<>:"/\|?*` or control characters.
- **Paths**: Must be absolute when processed; relative to `library_root` in config.
- **Rate Limits**: Max 60 requests per minute for Discogs API.
