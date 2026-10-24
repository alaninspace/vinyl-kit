---
name: deploy-docs
description: Deploy the VinylKit docs website (vinylkit.app) to CogitoVM over SSH. Use when asked to deploy, release, publish or push the docs site live, or after docs/ or src/docs_web/ changes the user wants live. Validates, tags docs-v<X.Y.Z>, copies the committed files to the VM and rebuilds the vinylkit-docs container.
---

# Deploy the docs website

The docs site runs as the `vinylkit-docs` container on CogitoVM, in `/srv/apps/vinylkit-docs`, behind the shared Caddy gateway. There is no CI deploy: GitHub cannot reach the VM, because SSH is open only to the operator's home IP. Deploy from the operator's machine with the `CogitoVM` SSH alias in `~/.ssh/config`.

**Never touch Caddy.** The live drop-in `/srv/apps/caddy/conf.d/vinylkit.caddy` (public `/metrics` 404, internal `:9180` metrics relay) belongs to the ErgoSum repo. Do not copy, edit or reload it from here.

Every command below works in both PowerShell 7 and zsh. Run them from the repo root.

## 1. Preconditions

- SSH works: `ssh -o BatchMode=yes -o ConnectTimeout=10 CogitoVM "echo ok"`. If it times out, the operator is probably away from home: stop and tell them.
- On `main`, nothing uncommitted that should ship, and `main` is pushed (`git status`, `git push origin main`). Only committed files are deployed.
- Pick the docs version: the next one after the newest `docs-v*` tag (`git tag --list "docs-v*" --sort=-v:refname`). Set it in both places, then commit:
  - `pyproject.toml`: `[tool.vinylkit.docs] version`
  - `src/docs_web/main.py`: the `docs_ver` fallback in `get_versions()`
- A docs-only release does not change the CLI version, `Formula/` or `scoop/`.

## 2. Validate

```
uv run pytest
uv run ruff check .
uv run mypy src/
```

All three must pass. `.\.deploy\deploy.ps1` runs the same checks on Windows.

## 3. Tag

The tag records what was deployed. It triggers nothing.

```
git tag docs-v<X.Y.Z>
git push origin docs-v<X.Y.Z>
```

## 4. Package and upload

```
git archive --format=tar.gz -o build/vinylkit-docs.tar.gz docs-v<X.Y.Z> Dockerfile docker-compose.yml requirements.txt pyproject.toml README.md src docs
scp build/vinylkit-docs.tar.gz CogitoVM:/tmp/vinylkit-docs.tar.gz
```

`build/` is git-ignored. The archive is built from the tag, not the working tree.

## 5. Rebuild on the VM

```
ssh CogitoVM 'set -e; cd /srv/apps/vinylkit-docs; rm -rf src docs; tar -xzf /tmp/vinylkit-docs.tar.gz; rm /tmp/vinylkit-docs.tar.gz; sudo docker compose up -d --build; sudo docker compose ps --format "{{.Name}} {{.Status}}"'
```

`src` and `docs` are removed first so deleted pages and assets do not linger. The container keeps its name, so Caddy needs no reload.

## 6. Verify

```
curl -s https://vinylkit.app/docs/readme | grep -o "v<X.Y.Z>"
curl -s -o /dev/null -w "%{http_code}\n" https://vinylkit.app/metrics
```

The first prints the new docs version (sidebar footer). The second must print `404`; anything else means the Caddy drop-in changed, so tell the operator. Also open any page or asset the release added, and check it answers `200`.

If the container does not come up: `ssh CogitoVM 'cd /srv/apps/vinylkit-docs && sudo docker compose logs --tail 50'`.
