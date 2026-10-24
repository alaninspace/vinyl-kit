---
name: release
description: Commit, release and publish VinylKit changes the same way every time, and verify that the CLI build, GitHub release, Homebrew/Scoop manifests and the vinylkit.app docs site all line up. Use whenever you are about to commit or offer to commit, when asked to release, ship, publish, tag or push, or before calling a code or docs task done. A commit to main is a release, not just a commit.
---

# Release VinylKit

Committing to `main` here means shipping: a CLI change needs a new version tag, which runs the GitHub build, and the docs site has to show that version. Don't offer a bare "commit?". Offer the whole release, naming what goes out, e.g. "Commit and release v0.16.5 + docs-v1.0.16?".

Run every step in order. Don't skip one because it "probably doesn't apply". Each step says when it applies.

## 1. Classify the change

Look at `git status` and `git diff --stat` against `origin/main`.

| What changed | Release type |
|---|---|
| Anything under `src/vinylkit/`, runtime deps in `pyproject.toml` | **CLI release**: CLI version bump, `v*` tag, build. Also a docs release, since the site shows the CLI version. |
| Only `docs/`, `src/docs_web/`, `README.md` | **Docs release**: docs version bump and deploy only. |
| Only `tests/`, `scripts/`, `.github/`, `.claude/`, agent files | **No release**: commit and push, no version bump. Tell the user it's not a release. |

CLI bump size: patch for fixes, minor for new features or flags, major for breaking changes. If the newest `## [vX.Y.Z]` in `CHANGELOG.md` has no matching `v` tag on origin, that version hasn't shipped yet: add to it instead of bumping again.

## 2. Docs sweep (CLI and docs releases)

Check each of these against the diff, and say in your summary which ones you changed and which didn't need changes:

- `docs/configuration.md`: every new or changed setting, flag and allowed value, with an example.
- `docs/user-guide.md` and `docs/examples.md`: behaviour changes and new flags. Every new example in `examples.md` needs a test in `tests/test_examples_coverage.py`.
- Help text: `epilog` strings and `help=` on changed `@click.option`s.
- `CHANGELOG.md` (CLI releases only): a `## [vX.Y.Z] - YYYY-MM-DD` entry (today's date) with Added/Fixed/Changed sections. The release workflow publishes this text as the GitHub release notes, so it must exist before tagging. Docs-only releases don't get an entry; the CHANGELOG follows CLI versions.
- `README.md`: only if user-facing behaviour shown there changed.

## 3. Bump versions

Get the next numbers from the tags: `git tag --list "v*" --sort=-v:refname` and `git tag --list "docs-v*" --sort=-v:refname`.

- **Docs version** (every CLI or docs release): `pyproject.toml` `[tool.vinylkit.docs] version` and the `docs_ver` fallback in `src/docs_web/main.py`.
- **CLI version** (CLI releases only):
  - `pyproject.toml` `[project] version`
  - `src/docs_web/main.py` `cli_ver` fallback
  - `Formula/vinyl-kit.rb`: `version` and both release URLs
  - `scoop/vinylkit.json`: `version` and `url`
  - run `uv lock` so `uv.lock` picks up the new version

Leave the sha256/hash values alone. The release workflow rewrites them after the build.

## 4. Validate

```
uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy src/
```

Everything must pass (`tests/test_version_sync.py` catches missed version strings). Fix failures before going on.

## 5. Commit and push

Only after the user says yes to the release you offered. Stage tracked changes plus new files that belong to the change, and never stage stray local files such as `.claude/launch.json`. Use a conventional commit message (`fix:`, `feat:`, `docs:`) that mentions the versions, e.g. `(v0.16.5 / docs-v1.0.16)`, and ends with the attribution line. Then `git push origin main`.

## 6. Build the CLI (CLI releases only)

```
git tag vX.Y.Z
git push origin vX.Y.Z
gh run list --workflow release_vinylkit-cli.yml --limit 1
gh run watch <run-id> --exit-status
```

Run the watch in the background (it takes about 5 minutes) and do step 7 prep meanwhile, but don't deploy the docs until the build passes: the site must never advertise a version that has no release. When the build passes, `git pull origin main` to get the bot's `chore: update release checksums` commit.

If the build fails: read the logs (`gh run view <run-id> --log-failed`), fix, and release as the next patch version. Don't move or re-push an existing tag.

## 7. Deploy the docs (CLI and docs releases)

Follow the `deploy-docs` skill (`.claude/skills/deploy-docs/SKILL.md`): SSH check, `docs-vX.Y.Z` tag, archive from the tag, upload, rebuild the container. If SSH to CogitoVM times out, the operator is away from home: stop and say the docs deploy is still pending.

## 8. Verify everything lines up

```
uv run python .claude/skills/release/verify_release.py
```

Add `--docs-only` for a docs release. The script checks:

- the version fallbacks in `src/docs_web/main.py` and the CHANGELOG entry
- nothing unpushed, and both tags on origin
- the release workflow succeeded, and the GitHub release is published with all 6 assets and non-empty notes
- the Homebrew and Scoop versions and checksums on `origin/main` match the downloaded release assets
- vinylkit.app shows both versions, and public `/metrics` is still 404

Then fetch each docs page the release changed and check it returns 200 and contains the new text.

Every check must pass before you report the release as done. If one fails, fix the cause (not the check) and run it again.

## 9. Report

Give a short table of what was released (CLI version and run link, docs version, GitHub release URL) plus the verify result. Name anything still pending, such as a docs deploy blocked on SSH.
