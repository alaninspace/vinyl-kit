# Documentation: Deploying vinyl-kit Documentation Web App to CogitoVM

This document describes where the `docs_web` application runs and how a release reaches it.

## 1. Infrastructure Architecture

- **Host VM:** CogitoVM (SSH alias `CogitoVM`; SSH is open only to the operator's home IP)
- **Container Name:** `vinylkit-docs` (Python 3.12 FastAPI/Uvicorn application) in `/srv/apps/vinylkit-docs`
- **Memory Limits:** Bounded at `memory: 96M` limit (`reservations: 32M`) inside `docker-compose.yml`.
- **Reverse Proxy & SSL:** Caddy gateway container (`caddy_gateway`) running on `CogitoVM`.
- **Custom Domain:** `https://vinylkit.app/`
- **DNS Zone:** `vinylkit.app` in Azure DNS Zone (Subscription 3: `Sinkers Sub 3`, Resource Group `Sub3RG`).
- **SSL Certificate:** Free automatic Let's Encrypt TLS managed by Caddy.

---

## 2. Caddy Configuration

The Caddy drop-in `/srv/apps/caddy/conf.d/vinylkit.caddy` is owned by the ErgoSum repository (`infra-provisioning/caddy/conf.d/vinylkit.caddy`). It routes `vinylkit.app` and `www.vinylkit.app` to `vinylkit-docs:8000`, answers public `/metrics` with 404 and runs an internal `:9180` relay for VictoriaMetrics. Deploys from this repo never touch it.

---

## 3. Releases

- **Docs website:** deployed by hand from the operator's machine with the `deploy-docs` agent skill (`.claude/skills/deploy-docs/SKILL.md`). The `docs-v*` tag records what was deployed and triggers nothing. There is no CI deploy: GitHub's runners cannot reach the VM over SSH.
- **Standalone CLI (`release_vinylkit-cli.yml`):** tags matching `v*` (excluding `docs-v*` tags) build binaries for macOS, Windows and Linux and create a GitHub Release.

---

## 4. Local Validation

```powershell
.\.deploy\deploy.ps1
```
