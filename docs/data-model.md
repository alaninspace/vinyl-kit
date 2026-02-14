# Data Model: VinylKit CLI Manager

## Core Entities

### DiscogsRelease
Represents metadata fetched from the Discogs API.
- **id**: `int` (Primary Key from Discogs)
- **artists**: `list[str]`
- **title**: `str`
- **tracklist**: `list[TrackInfo]`
- **year**: `int | None`
- **released**: `str | None`
- **country**: `str | None`
- **label**: `str | None` (Primary label name)
- **catno**: `str | None` (Primary catalogue number)
- **labels**: `list[LabelInfo]` (Full list of labels)
- **companies**: `list[CompanyInfo]` (Companies involved)
- **formats**: `list[FormatInfo]` (Physical formats)
- **identifiers**: `list[IdentifierInfo]` (Barcodes, Matrix numbers)
- **extraartists**: `list[ExtraArtistInfo]` (Credits like Producer, Design)
- **genres**: `list[str]`
- **styles**: `list[str]`
- **notes**: `str | None`
- **images**: `list[ImageInfo]`
- **uri**: `str | None` (Discogs release URL)
- **master_id**: `int | None` (Discogs master release ID)
- **master_url**: `str | None` (Discogs master release URL)
- **artists_sort**: `str | None` (Discogs normalized artist sort name)
- **data_quality**: `str | None` (Discogs data quality rating, e.g., "Correct")
- **format_quantity**: `int | None` (Number of physical items in the release)

### LabelInfo
- **name**: `str`
- **catno**: `str | None`

### CompanyInfo
- **name**: `str`
- **entity_type_name**: `str`

### FormatInfo
- **name**: `str`
- **qty**: `str`
- **descriptions**: `list[str]`

### IdentifierInfo
- **type**: `str`
- **value**: `str`
- **description**: `str | None`

### ExtraArtistInfo
- **name**: `str`
- **role**: `str`

### TrackInfo
- **position**: `str` (e.g., "A1", "B2")
- **title**: `str`
- **artists**: `list[str]` (Track-specific artists)
- **side**: `str | None` (Extracted from position, e.g., "A")
- **extraartists**: `list[ExtraArtistInfo]` (Track-level credits, e.g., remix, written-by)
- **duration**: `str | None` (Track duration from Discogs, e.g., "5:32")

### RateLimitInfo
Live rate limit telemetry updated on every Discogs API response. Intentionally **mutable** (not frozen) since fields are updated in-place.
- **limit**: `int | None` (`X-Discogs-Ratelimit` — 60 for authenticated, 25 for unauthenticated)
- **used**: `int | None` (`X-Discogs-Ratelimit-Used`)
- **remaining**: `int | None` (`X-Discogs-Ratelimit-Remaining`)
- **last_updated**: `float` (Epoch timestamp of the last update)
- **peak_used**: `int` (High-water mark of `used` across the session)

### AudioFile
Represents a physical file on the user's disk.
- **path**: `pathlib.Path`
- **extension**: `str` (mp3, flac)
- **tag_status**: `TagStatus` (UNTAGGED, PARTIAL, TAGGED)
- **sample_rate**: `int | None`
- **bit_depth**: `int | None`
- **duration**: `float | None`

### AppConfig
User settings stored in TOML.
- **library_root**: `pathlib.Path`
- **recordings_root**: `pathlib.Path | None`
- **consumer_key**: `str | None`
- **consumer_secret**: `str | None`
- **discogs_token**: `str | None`
- **discogs_secret**: `str | None` (for OAuth)
- **auth_mode**: `AuthMode` (AUTO, TOKEN, OAUTH, KEY_SECRET, NONE)
- **tag_mode**: `TagMode` (REPLACE, MERGE)
- **naming_pattern**: `str` (Default: `{artist}/{year} - {album}/{track_number} - {title}`)
- **image_handling**: `ImageHandling` (EMBED, SAVE, BOTH, NONE)
- **collect_all_artwork**: `bool` (Download all release images)
- **artwork_subdir**: `str` (Subdirectory for additional images)
- **backup_enabled**: `bool`
- **backup_dir**: `pathlib.Path | None`
- **info_filename**: `str` (Default: release_info.txt)
- **artwork_filename**: `str` (Default: folder.jpg)
- **track_numbering**: `TrackNumbering` (NUMERIC, ORIGINAL, PER_SIDE)
- **disc_mapping**: `DiscMapping` (PHYSICAL, SINGLE, PER_SIDE, ORIGINAL)
- **search_page_size**: `int` (Default: 5)
- **default_format**: `list[str]` (Default: ["Vinyl"])
- **auto_move**: `bool` (Default: false)
- **delete_after_migration**: `bool` (Default: false)
- **replace_artwork_on_migration**: `bool` (Default: true)
- **replace_tags_on_migration**: `bool` (Default: true)
- **skip_tags**: `list[str]` (Canonical tag names to exclude from writing; default: empty)
- **log_level**: `str` (Default: "INFO")
- **log_to_file**: `bool` (Default: true)
- **log_file**: `pathlib.Path | None`
- **log_rotation**: `str` (Default: "5 MB")
- **log_retention**: `int` (Default: 5)

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
