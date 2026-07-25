# Documentation: Deploying vinyl-kit Documentation Web App to CogitoVM

This document describes the CogitoVM self-hosted infrastructure, local validation script, and GitHub Actions CI/CD workflows for the `docs_web` application.

## 1. Infrastructure Architecture

- **Host VM:** CogitoVM (`20.211.73.228`)
- **Container Name:** `vinylkit-docs` (Python 3.12 FastAPI/Uvicorn application)
- **Memory Limits:** Bounded at `memory: 96M` limit (`reservations: 32M`) inside `docker-compose.yml`.
- **Reverse Proxy & SSL:** Caddy gateway container (`caddy_gateway`) running on `CogitoVM`.
- **Custom Domain:** `https://vinylkit.app/`
- **DNS Zone:** `vinylkit.app` in Azure DNS Zone (Subscription 3: `Sinkers Sub 3`, Resource Group `Sub3RG`).
  - A Record `@` -> `20.211.73.228`
- **SSL Certificate:** Free automatic Let's Encrypt TLS managed by Caddy.

---

## 2. Decoupled Routing & Caddy Configuration

To ensure zero coupling between `ErgoSum`'s infrastructure stack and `vinyl-kit`, Caddy uses modular drop-in site definitions:
- Main Caddyfile includes: `import /etc/caddy/conf.d/*.caddy`
- `vinyl-kit` deploys its own `/srv/apps/caddy/conf.d/vinylkit.caddy`:
```caddy
vinylkit.app, www.vinylkit.app {
    reverse_proxy vinylkit-docs:8000
}
```

---

## 3. GitHub Actions CI/CD Workflows

The repository maintains two independent workflows:

1. **Docs Website Deployment (`main_vinylkit-webapp.yml`):**
   - **Trigger:** Tags matching `docs-v*` (e.g., `docs-v1.0.2`) or manual `workflow_dispatch`.
   - **Action:** Syncs code to `CogitoVM`, deploys `vinylkit-docs` Docker container, and reloads Caddy gateway.
2. **Standalone CLI Releases (`release_vinylkit-cli.yml`):**
   - **Trigger:** Tags matching `v*` (excluding `docs-v*` tags).
   - **Action:** Compiles standalone binaries for macOS, Windows, and Linux, creating a GitHub Release.

---

## 4. Local Validation & Deployment

Run the local validation script before releasing:

```powershell
.\.deploy\deploy.ps1
```

To release a new version of the docs website:
```bash
git add .
git commit -m "docs: update documentation webapp (v1.0.2)"
git push origin main
git tag docs-v1.0.2
git push origin docs-v1.0.2
```
