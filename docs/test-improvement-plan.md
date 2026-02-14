# Test Suite Improvement Plan

## Current State

- 54 tests across 10 files
- No `conftest.py` — fixtures duplicated across files
- Config isolation broken in `test_cli.py` (can read/write real user config)
- All tagging tests mock mutagen — no real audio file validation
- Several CLI commands have zero test coverage

---

## Phase 1: Foundation (Config Isolation & Shared Fixtures)

### 1.1 Create `tests/conftest.py`

Centralize shared fixtures to eliminate duplication and ensure consistent isolation.

**Fixtures to extract:**

| Fixture | Current Location | Notes |
|---------|-----------------|-------|
| `runner` | test_cli.py, test_collisions.py, test_examples_coverage.py, test_migrate.py | Must include `VINYLKIT_CONFIG` env var isolation |
| `create_mock_release()` | test_collisions.py, test_examples_coverage.py, test_migrate.py | Helper for building `DiscogsRelease` with sensible defaults |
| `mock_discogs` | test_examples_coverage.py, test_migrate.py | Shared Discogs client mock |

**Key requirement:** Every fixture that invokes CLI commands must isolate config:
```python
@pytest.fixture
def runner(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setenv("VINYLKIT_CONFIG", str(config_path))
    return CliRunner()
```

### 1.2 Fix `test_cli.py` Runner Fixture

Replace the bare `CliRunner()` (line 12) with the isolated version from conftest. Remove the local fixture definition entirely.

### 1.3 Fix Test Naming

Rename `testcalculate_track_and_disc_logic` → `test_calculate_track_and_disc_logic` in `test_tagging.py:76` for consistency.

---

## Phase 2: Real Audio File Integration Tests

The highest-value addition. Create tests that write actual tags to real audio files and verify them.

### 2.1 Generate Test Audio Fixtures

Create minimal valid MP3 and FLAC files for testing. Options:
- Use `mutagen` to create minimal valid files programmatically
- Bundle tiny silent audio files as test fixtures in `tests/fixtures/`

Provide a conftest fixture:
```python
@pytest.fixture
def mp3_file(tmp_path) -> Path:
    """Create a minimal valid MP3 file."""
    ...

@pytest.fixture
def flac_file(tmp_path) -> Path:
    """Create a minimal valid FLAC file."""
    ...
```

### 2.2 Tag Round-Trip Tests

Test the full cycle: write tags → read them back → assert correctness.

**Scenarios to cover:**

| Scenario | Format | Details |
|----------|--------|---------|
| Basic single-artist release | MP3 | Artist, title, album, year, track number, genre |
| Basic single-artist release | FLAC | Same as above for Vorbis comments |
| Multi-artist release | Both | Verify artist joining/formatting |
| Replace mode | Both | Existing tags are cleared before writing |
| Merge mode | Both | Existing tags are preserved, new tags added |
| Artwork embedding | Both | Embed cover art, verify image data round-trips |
| Multi-disc release | Both | Disc number and track numbering correct |
| Vinyl-specific metadata | Both | Side, position fields written correctly |

### 2.3 Realistic Discogs Data

Use realistic (but static) release data modeled on real Discogs entries, see 2026-02-08_auzziehood_collection.csv for examples:
- Single LP (e.g., 2 sides, 8 tracks)
- Double LP (e.g., 4 sides, 16 tracks)
- 12" single (e.g., 2 sides, 2-4 tracks)
- Compilation / various artists

---

## Phase 3: Missing CLI Command Tests

### 3.1 `rename` Command

- Dry-run by default (no `--commit`) — verify no files moved
- With `--commit` — verify files moved to correct paths
- Interactive ID prompting when `--id` not provided
- Error when target files already exist (collision handling)

### 3.2 `scan` Command

- Scan directory with mixed audio files — verify output table
- Scan directory with no audio files — verify message
- Scan with tagged vs untagged files — verify status reporting

### 3.3 `auth` Commands

- `auth login` — mock OAuth flow, verify credentials saved to config
- `auth identity` — mock API response, verify user info displayed
- `auth identity` when not authenticated — verify error message

### 3.4 `config show` Command

- Verify output displays all config keys
- Verify default values shown when no config file exists

### 3.5 `config set` Command

- Set each value type (string, bool, path, int)
- Invalid key — verify error
- Invalid value for type — verify error

---

## Phase 4: Behavior-Focused Test Rewrites

### 4.1 Replace Mock-Checking with Behavior Assertions

**Current (test_tagging_modes.py):**
```python
assert mock_audio.delete.called        # checks implementation
assert not mock_audio.delete.called    # checks implementation
```

**Target:**
```python
# Replace mode: only new tags present
audio = mutagen.MP3(tagged_file)
assert audio["TIT2"].text == ["New Title"]
assert "TXXX:old_custom_tag" not in audio

# Merge mode: both old and new tags present
audio = mutagen.MP3(tagged_file)
assert audio["TIT2"].text == ["New Title"]     # new tag applied
assert audio["TPE2"].text == ["Old Artist"]     # old tag preserved
```

### 4.2 Edge Cases to Add

- Tracks with no side information (`side=None`)
- Special characters in artist/title (accents, ampersands, slashes)
- Very long filenames hitting OS path limits
- Empty tracklist
- Release with no artwork

---

## Phase 5: Utility Function Tests

### 5.1 `utils.py` Functions

| Function | Test Cases |
|----------|-----------|
| `backup_file()` | Creates backup copy, backup naming convention, source unchanged |
| `sanitize_filename()` | Strips illegal chars, handles unicode, truncates length |
| `ensure_absolute()` | Relative → absolute, already absolute unchanged |

### 5.2 `naming.py` Edge Cases

- Artist names with "The" prefix
- Multi-artist formatting
- Filename collision avoidance (incrementing suffix)

---

## Phase 6: Config Round-Trip Test

Verify config survives a full write → read cycle:
```python
def test_config_round_trip(tmp_path):
    # Set various config values via CLI
    # Read them back via config show
    # Assert all values match
```

Test all value types: strings, booleans, paths, integers.

---

## Implementation Order

| Priority | Phase | Effort | Impact |
|----------|-------|--------|--------|
| P0 | Phase 1 (conftest + isolation fix) | Small | Fixes live config bug, prevents future isolation issues |
| P1 | Phase 2 (real audio tests) | Medium | Highest confidence gain — proves tagging actually works |
| P1 | Phase 3.1-3.2 (rename + scan tests) | Medium | Core commands currently untested |
| P2 | Phase 4 (behavior rewrites) | Small | Better test quality, less brittle |
| P2 | Phase 3.3-3.5 (auth + config tests) | Medium | Important but lower risk commands |
| P3 | Phase 5-6 (utilities + config) | Small | Completeness |
