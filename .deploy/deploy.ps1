# PowerShell Validation & Deployment Script for vinyl-kit docs_web
# Validates tests, linter, and type checker before deploying to CogitoVM.

$ErrorActionPreference = "Stop"

Write-Host "Starting Validation & Deployment Script for CogitoVM" -ForegroundColor Cyan

# 1. Run Tests
Write-Host "1. Running test suite..." -ForegroundColor Yellow
uv run pytest
if ($LASTEXITCODE -ne 0) {
    Write-Error "Tests failed! Aborting deployment."
}

# 2. Run Ruff Lint Checks
Write-Host "2. Running linter (ruff)..." -ForegroundColor Yellow
uv run ruff check .
if ($LASTEXITCODE -ne 0) {
    Write-Error "Linter checks failed! Aborting deployment."
}

# 3. Run Mypy Type Checks
Write-Host "3. Running type checker (mypy)..." -ForegroundColor Yellow
uv run mypy src/
if ($LASTEXITCODE -ne 0) {
    Write-Error "Type checks failed! Aborting deployment."
}

Write-Host "Validation Passed! Pushing docs release tag to trigger GitHub Action deployment..." -ForegroundColor Green

# Read current docs version from pyproject.toml
$pyproject = Get-Content "pyproject.toml" -Raw
if ($pyproject -match '\[tool\.vinylkit\.docs\]\s*version\s*=\s*"([^"]+)"') {
    $docsVer = $matches[1]
    $tagName = "docs-v$docsVer"
    Write-Host "Detected docs version: $docsVer (Tag: $tagName)" -ForegroundColor Green
    
    # Prompt for confirmation or push tag
    Write-Host "To deploy via GitHub Actions, commit your changes and run:" -ForegroundColor Cyan
    Write-Host "git tag $tagName && git push origin main --tags" -ForegroundColor White
} else {
    Write-Error "Could not detect docs version in pyproject.toml."
}
