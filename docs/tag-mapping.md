# Tag Mapping Reference

VinylKit writes up to 32 tags per audio file using metadata from the Discogs API. This document is the authoritative reference for what gets written, where it comes from, and how to control it.

---

## Overview

Tags are organized into three categories:

1. **Standard tags** (15) — well-known fields recognized by all music players and library managers (artist, album, genre, etc.)
2. **Ecosystem-recognized tags** (10) — custom fields that use naming conventions shared by Picard, beets, foobar2000, and other tools (CATALOGNUMBER, STYLE, LABEL, etc.)
3. **Discogs-specific tags** (7) — metadata unique to Discogs, prefixed with `DISCOGS_` to avoid collisions

All tag names below use their **canonical name** — the lowercase identifier used in the `skip_tags` config setting.

---

## Standard Tags

| Canonical Name | MP3 Frame | FLAC Key | Source |
|---|---|---|---|
| `artist` | TPE1 | `artist` | `release.artists` (comma-separated for MP3, list for FLAC) |
| `albumartist` | TPE2 | `albumartist` | `release.artists` (always set, same as artist) |
| `title` | TIT2 | `title` | `track.title` |
| `album` | TALB | `album` | `release.title` |
| `date` | TDRC | `date` | `release.year` (year only, e.g. "1995") |
| `releasedate` | TDRL | `releasedate` | `release.released` (full date, e.g. "1995-06-01") |
| `tracknumber` | TRCK | `tracknumber` | Calculated based on `track_numbering` config |
| `discnumber` | TPOS | `discnumber` | Calculated based on `disc_mapping` config |
| `publisher` | TPUB | `organization` | `release.label` (primary label) |
| `genre` | TCON | `genre` | `release.genres` |
| `composer` | TCOM | `composer` | Extracted from extraartists with roles: Written-By, Composer, Music By, Lyrics By |
| `remixer` | TPE4 | `remixer` | Extracted from extraartists with roles: Remix, Remixed By, Remixer |
| `copyright` | TCOP | `copyright` | Companies where `entity_type_name` contains "Copyright" |
| `media` | TMED | `media` | First format name (e.g. "Vinyl", "CD") |
| `artistsort` | TSOP | `artistsort` | `release.artists_sort` (Discogs normalized sort name) |

---

## Ecosystem-Recognized Tags

These use naming conventions shared by MusicBrainz Picard, beets, foobar2000, and other tools. They are stored as TXXX frames (MP3) or Vorbis comment keys (FLAC).

| Canonical Name | MP3 TXXX desc | FLAC Key | Source |
|---|---|---|---|
| `style` | STYLE | `style` | `release.styles` |
| `catalognumber` | CATALOGNUMBER | `catalognumber` | Primary catno or all label catnos |
| `side` | SIDE | `side` | `track.side` (extracted from position) |
| `label` | LABEL | `label` | All label names |
| `format` | FORMAT | `format` | Format strings (e.g. "1x Vinyl (12\", 33 ⅓ RPM)") |
| `companies` | COMPANIES | `companies` | All companies with entity types |
| `credits` | CREDITS | `credits` | Release + track extraartists (role: name) |
| `barcode` | BARCODE | `barcode` | Barcodes from identifiers |
| `country` | COUNTRY | `country` | `release.country` |
| `discogs_position` | DISCOGS_POSITION | `discogs_position` | `track.position` (original vinyl position) |

---

## Discogs-Specific Tags

These carry metadata unique to Discogs and use the `DISCOGS_` prefix to clearly identify their origin.

| Canonical Name | MP3 TXXX desc | FLAC Key | Source |
|---|---|---|---|
| `discogs_release_id` | DISCOGS_RELEASE_ID | `discogs_release_id` | `release.id` |
| `discogs_release_url` | DISCOGS_RELEASE_URL | `discogs_release_url` | `release.uri` |
| `discogs_master_id` | DISCOGS_MASTER_ID | `discogs_master_id` | `release.master_id` |
| `discogs_master_url` | DISCOGS_MASTER_URL | `discogs_master_url` | `release.master_url` |
| `discogs_notes` | DISCOGS_NOTES | `discogs_notes` | `release.notes` |
| `discogs_data_quality` | DISCOGS_DATA_QUALITY | `discogs_data_quality` | `release.data_quality` |
| `discogs_format_quantity` | DISCOGS_FORMAT_QUANTITY | `discogs_format_quantity` | `release.format_quantity` |

---

## Artwork

| Canonical Name | MP3 Frame | FLAC Block | Source |
|---|---|---|---|
| `artwork` | APIC | PICTURE | Downloaded image bytes (front cover, type 3) |

---

## Credits and Composer/Remixer Extraction

The `credits` tag combines **release-level** and **track-level** extraartists from Discogs into a single field. For example, a release with a mastering engineer and a track with a remix credit will produce:

```
Mastered By: Bob Ludwig, Remix: DJ Shadow
```

The `composer` and `remixer` tags are extracted from the same combined extraartists list using role matching:

- **Composer roles**: Written-By, Written By, Composer, Music By, Lyrics By
- **Remixer roles**: Remix, Remixed By, Remixer

Role matching is case-insensitive and uses substring matching (e.g. "Co-Written-By" would also match).

---

## Intentionally Skipped Discogs Fields

These fields are available in the Discogs API but are **not** written as tags:

| Field | Reason |
|---|---|
| `videos` | Not audio metadata |
| `community` (have/want/rating) | Volatile social data, not release metadata |
| `series` | Extremely rare, no standard tag mapping |
| `released_formatted` | Redundant with `released` |
| `estimated_weight` | Physical shipping data |
| `num_for_sale` / `lowest_price` | Marketplace data |
| `date_added` / `date_changed` | Discogs database timestamps |

---

## Controlling Tags with `skip_tags`

You can exclude any tag from being written by adding its **canonical name** to the `skip_tags` config setting:

```bash
# Skip genre and style tags
vinylkit config set skip_tags "genre,style"

# Skip all Discogs-specific metadata
vinylkit config set skip_tags "discogs_release_id,discogs_master_id,discogs_master_url,discogs_notes,discogs_data_quality,discogs_format_quantity"

# Skip artwork embedding (artwork files are still saved per image_handling config)
vinylkit config set skip_tags "artwork"

# Clear the skip list (write all tags)
vinylkit config set skip_tags "none"
```

The canonical names are the lowercase identifiers listed in the first column of each table above.
