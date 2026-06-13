# Documentation: Deploying vinyl-kit Documentation Web App

This document describes the Azure infrastructure, local deployment automation, and GitHub Actions CI/CD workflows for the `docs_web` application.

## 1. Infrastructure Architecture

* **Target Web App:** `vinylkit-webapp` (or your custom app name)
  * **Type:** Linux App Service (Python 3.12)
  * **Plan:** `vinylkit-appservice-plan` (Basic tier)
  * **Resource Group:** `<WEBAPP_RESOURCE_GROUP>`
  * **Subscription:** `<AZURE_WEBAPP_SUBSCRIPTION_ID>` (<YOUR_WEBAPP_SUBSCRIPTION_NAME>)
* **Custom Domain & DNS:**
  * **Domain:** `https://vinylkit.app/`
  * **DNS Zone:** `vinylkit.app` in `<DNS_RESOURCE_GROUP>`
  * **Subscription:** `<AZURE_DNS_SUBSCRIPTION_ID>` (<YOUR_DNS_SUBSCRIPTION_NAME>)
  * **SSL Certificate:** App Service Managed Certificate (SNI Enabled)
* **Redirection & HTTPS Settings:**
  * **HTTPS Only:** Enabled (`httpsOnly=true` on App Service config)
  * **Domain Redirection:** Custom HTTP middleware on FastAPI redirects all default `*.azurewebsites.net` requests with a 301 Redirect to the custom domain `https://vinylkit.app`.

---

## 2. Local Configuration & Deployment

To support multi-device development (e.g., switching between a desktop and a laptop) without checking private subscription IDs or app names into version control, the deployment script reads configuration parameters from a local file that is ignored by Git.

### 1. Create Local Config File

On each development machine, create a file named `.azure/local-config.json` in your project root:

```json
{
    "subscriptionId": "<YOUR_AZURE_SUBSCRIPTION_ID>",
    "resourceGroup": "<YOUR_TARGET_RESOURCE_GROUP>",
    "webAppName": "<YOUR_TARGET_WEB_APP_NAME>"
}
```

*Note: This file is excluded from version control to prevent leaks.*

### 2. Pre-requisites

1. **Azure CLI:** Install and log in:

   ```powershell
   az login
   ```

2. **Dependencies:** Ensure Python 3.12+ and `uv` package manager are installed.

### 3. Run Local Deployment

Run the deployment script from your project root:

```powershell
.\.azure\deploy.ps1
```

The script will automatically validate tests, check type-safety, package your directory, switch the Azure CLI context to your target subscription, and deploy the zip.

---

## 3. GitHub Actions CI/CD Workflow

The file `.github/workflows/main_vinylkit-webapp.yml` contains the deployment configuration. It performs a ZIP deployment using modern GitHub Actions.

### Dual triggers

The workflow supports two modes of execution:

1. **Automated (Git Tags):** Triggers automatically whenever you push a tag matching `v*` (e.g. `v1.0.1`).
2. **Manual (Workflow Dispatch):** Can be triggered manually via the **Actions** tab on your GitHub repository.

### Workflow Configuration

```yaml
name: Deploy Docs Web to Azure App Service

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Package application files
      run: |
        zip -r deploy.zip src docs requirements.txt README.md

    - name: Deploy to Azure Web App
      uses: azure/webapps-deploy@v3
      with:
        app-name: 'vinylkit-webapp'
        publish-profile: ${{ secrets.AzureAppService_PublishProfile_<SECRET_HASH> }}
        package: './deploy.zip'
```

Configure your GitHub repository secret `AzureAppService_PublishProfile_<SECRET_HASH>` with the Web App's XML Publishing Profile.

### How to Commit and Push Tags (Triggers Deployment)

To trigger the deployment, commit your changes, push them to `main`, create a tag (e.g., `v1.0.1`), and push the tag.

#### Option 1: Via CMD / Terminal

Run the following git commands:

```bash
# 1. Stage and commit your changes
git add .
git commit -m "docs: bla bla"

# 2. Push commits to main branch
git push origin main

# 3. Create a tag matching the 'v*' pattern
git tag v1.0.1

# 4. Push the tag to GitHub (this triggers the action)
git push origin v1.0.1
```

#### Option 2: Via VS Code UI

1. **Commit your changes:**
   * Go to the **Source Control** tab (`Ctrl + Shift + G`).
   * Type your commit message in the text box and click **Commit**.
2. **Push commits:**
   * Click **Sync Changes** (or click the `...` menu and select **Push**).
3. **Create a Tag:**
   * Open the **Command Palette** (`Ctrl + Shift + P`).
   * Type `Git: Create Tag` and press Enter.
   * Enter your tag name (e.g., `v1.0.1`) and press Enter.
   * Press Enter again to skip the tag message.
4. **Push the Tag:**
   * Open the **Command Palette** (`Ctrl + Shift + P`).
   * Type `Git: Push (Follow Tags)` or `Git: Push Tags` and press Enter.

---

## 4. Verification & Health Checks

After deployment, verify the site status:

* **Custom Domain:** [https://vinylkit.app/docs/quickstart](https://vinylkit.app/docs/quickstart) (Returns `200 OK`)
* **Default Hostname:** [https://vinylkit-webapp.azurewebsites.net/docs/quickstart](https://vinylkit-webapp.azurewebsites.net/docs/quickstart) (Returns `301` redirecting to custom domain)

---

## 5. Setting Up GitHub Actions Secrets

To allow GitHub Actions to authenticate and deploy to your Web App, configure the repository secrets:

### 1. Download the Publishing Profile

Run the following command locally to output the Web App XML credentials:

```powershell
az webapp deployment list-publishing-profiles --resource-group <YOUR_TARGET_RESOURCE_GROUP> --name <YOUR_TARGET_WEB_APP_NAME> --xml
```

*Copy the entire XML output block.*

### 2. Save Secret in GitHub

1. Go to your repository on GitHub.
2. Navigate to **Settings** > **Secrets and variables** > **Actions**.
3. Click **New repository secret**.
4. Set the name to: `AzureAppService_PublishProfile_<SECRET_HASH>`
5. Paste the copied XML content as the value and save.
