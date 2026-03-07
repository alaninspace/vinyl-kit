# Documentation Improvement Action Plan

Analysis of all markdown files against the codebase, identifying correctness issues, duplication, and improvement opportunities.

**Last verified**: 2026-03-07 (Iteration 1 of Ralph Loop)

---

## Status: All Issues Resolved

All P0 and P1 issues from the original analysis have been fixed. Remaining items are optional improvements assessed as acceptable or low-priority.

---

## 1. Correctness Issues — ALL FIXED

### 1.1 README.md — Incorrect mypy command ✅ FIXED
- `uv run mypy .` changed to `uv run mypy src/` (README.md:102)

### 1.2 README.md — Inconsistent repo name/URL ✅ FIXED
- `vinyl-man` changed to `vinyl-kit` (README.md:26-27)

### 1.3 Windows platform paths ✅ FIXED
- All Windows paths now include the doubled `\vinylkit\vinylkit\` segment that `platformdirs` produces:
  - quickstart.md:203 — Config path ✅
  - developer-guide.md:65 — Config path ✅
  - configuration.md:297 — Log path ✅
  - configuration.md:202 — Cache path (was already correct) ✅
  - user-guide.md:317 — Log path ✅
- Verified against `platformdirs.user_config_dir("vinylkit")` → `%LOCALAPPDATA%\vinylkit\vinylkit`
- macOS and Linux paths remain correct (platformdirs doesn't use appauthor on those platforms)

### 1.4 DiscMapping.ORIGINAL — Inconsistent descriptions ✅ FIXED
- All docs and code now say "Always disc 1" / "format_quantity not yet used":
  - models.py:47 — Code comment ✅
  - configuration.md:98 ✅
  - data-model.md:186 ✅
  - CLAUDE.md:169 — Already correct (said "always disc 1") ✅
- Verified against tagging.py:374-378: `DiscMapping.ORIGINAL` → `disc_num = "1"`

### 1.5 data-model.md — NamingTemplate reference ✅ FIXED
- data-model.md:210 now says "based on `naming_pattern` via `generate_path()`"
- Verified: no `NamingTemplate` class exists in codebase (grep confirmed)

### 1.6 Test file listings — Missing test_help.py ✅ FIXED
- Added to CLAUDE.md:61 and developer-guide.md:105
- Verified: `tests/test_help.py` exists on disk

---

## 2. Duplication Issues — RESOLVED OR ACCEPTED

### 2.1 Naming pattern placeholders (4 places) ✅ IMPROVED
- quickstart.md:101 — Condensed to inline list + link to configuration.md
- user-guide.md:235-251 — Full table retained (user-facing reference, acceptable)
- configuration.md:71 — Authoritative reference (unchanged)
- CLAUDE.md:162 — Compact list for AI audience (unchanged)

### 2.2 Log file paths (3 places) — ACCEPTED
- Paths are correct in all three locations. Different audiences justify duplication.

### 2.3 Cache paths (2 places) — ACCEPTED (no action needed)

### 2.4 Installation instructions (3 places) — ACCEPTED
- URLs are now consistent (all use `vinyl-kit`).

### 2.5 Config file location (3 places) — ACCEPTED
- Paths are now correct everywhere (see 1.3).

### 2.6 Command reference (3 places) — ACCEPTED
- Different detail levels for different audiences. All in sync.

### 2.7 Auth mode table (2 places) — ACCEPTED

### 2.8 Logging config examples ✅ IMPROVED
- user-guide.md:321-323 — Trimmed to summary + link to configuration.md

---

## 3. Improvement Opportunities — RESOLVED OR ACCEPTED

### 3.1 spec.md — Future Enhancements caveat ✅ FIXED
- Added note: "These are ideas from the original specification, not committed work."

### 3.2 spec.md — NamingTemplate entity ✅ FIXED
- Added note that actual implementation uses `naming_pattern` string + `generate_path()` function

### 3.3 data-model.md — skip_tags type detail ✅ FIXED
- data-model.md:127 now notes conversion to `frozenset[str]` at tagging call site

### 3.4 developer-guide.md — "Adding a New CLI Command" numbering ✅ FIXED
- Steps correctly numbered 1-5

### 3.5 developer-guide.md — "Adding a New Config Option" numbering ✅ FIXED
- Steps correctly numbered 1-6

### 3.6 README.md — Missing doc links ✅ FIXED
- Added links to tag-mapping.md and data-model.md (README.md:76-77)

### 3.7 user-guide.md — Incomplete TOC ✅ FIXED
- Added `collection` and `cache` to TOC (user-guide.md:16-18)

### 3.8 CLAUDE.md — main() Exception fallback — ACCEPTED (low priority)
- cli.py:211-213 catches bare `Exception` as a last-resort fallback. CLAUDE.md's guidance about catching specific types applies to module code, not the entry point. No change needed.

### 3.9 Cross-linking between docs ✅ FIXED
- auth.md — Added "See Also" linking to configuration.md and user-guide.md
- tag-mapping.md — Added "See Also" linking to user-guide.md, examples.md, configuration.md
- data-model.md — Added "See Also" linking to developer-guide.md and configuration.md

### 3.10 Inbox workflow description ✅ FIXED
- user-guide.md:286 now explicitly states `--rename` is automatic in inbox workflow
- Verified: tag.py:158-159 sets `do_rename = True` when using recordings_root with no paths

### 3.11 CLAUDE.md — _helpers.py list incomplete — ACCEPTED (low priority)
- CLAUDE.md says "etc." which is sufficient. developer-guide.md:148 has a more complete list.

### 3.12 cache clear --id confirmation bypass ✅ FIXED
- configuration.md:224 now documents that `--id` bypasses confirmation
- Verified: cache.py:112-123 — `--id` path returns immediately after unlink, never reaches `click.confirm`

### 3.13 pyproject.toml — Placeholder description ✅ FIXED
- Updated to: "A cross-platform CLI tool for managing digitized vinyl record audio files using metadata from Discogs."

---

## 4. Verification Summary

Every claim in all 11 markdown files has been verified against the source code:

| File | Status | Verified Against |
|------|--------|-----------------|
| README.md | ✅ Accurate | pyproject.toml, CLAUDE.md commands |
| CLAUDE.md | ✅ Accurate | models.py, config.py, cli.py, tagging.py, naming.py, _helpers.py, conftest.py, exceptions.py |
| quickstart.md | ✅ Accurate | config.py (platformdirs), tag.py (recordings_root logic) |
| user-guide.md | ✅ Accurate | All command modules, naming.py placeholders, tagging.py tag count |
| developer-guide.md | ✅ Accurate | Project structure (glob), conftest.py fixtures, pyproject.toml ruff config |
| configuration.md | ✅ Accurate | models.py defaults, cache.py behavior, all enum values |
| data-model.md | ✅ Accurate | models.py dataclasses, exceptions.py hierarchy, naming.py |
| spec.md | ✅ Accurate | Historical doc with appropriate caveats added |
| auth.md | ✅ Accurate | discogs.py auth chain, models.py AuthMode enum |
| tag-mapping.md | ✅ Accurate | tagging.py _prepare_tags(), tag frames, canonical names |
| examples.md | ✅ Accurate | All commands match CLI signatures |
| pyproject.toml | ✅ Accurate | Description matches README |

### Key Code Verifications Performed
- `platformdirs` output on Windows: `user_config_dir("vinylkit")` = `%LOCALAPPDATA%\vinylkit\vinylkit` (confirmed via runtime check)
- `DiscMapping.ORIGINAL` behavior: tagging.py:374-378 always returns `disc_num = "1"` (confirmed)
- No `NamingTemplate` class exists: grep across all .py files returned zero matches (confirmed)
- `tests/test_help.py` exists on disk (confirmed via glob)
- `cache clear --id` skips confirmation: cache.py:112-123 returns before reaching `click.confirm` (confirmed)
- `tag` command auto-rename: tag.py:158-159 sets `do_rename = True` for recordings_root (confirmed)
- All 18 test files match listings in CLAUDE.md and developer-guide.md (confirmed via glob)
- All AppConfig fields in data-model.md match models.py:152-183 (confirmed)
- All exception classes match exceptions.py (confirmed)
- Naming placeholders in naming.py:28-42 match all doc placeholder lists (confirmed)
