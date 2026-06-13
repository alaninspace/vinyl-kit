# VinylKit Installer for Windows PowerShell
# Installs standalone binary to $HOME\.vinylkit\bin

$ErrorActionPreference = 'Stop'

Write-Host "[info] Detecting system..." -ForegroundColor Green

# Target Directory
$InstallDir = Join-Path $HOME ".vinylkit\bin"
Write-Host "[info] Installing to: $InstallDir" -ForegroundColor Green

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
}

# Download URL
$ZipUrl = "https://github.com/alaninspace/vinyl-kit/releases/latest/download/vinylkit-windows-amd64.zip"
$ZipPath = Join-Path $InstallDir "vinylkit.zip"

Write-Host "[info] Downloading latest Windows release..." -ForegroundColor Green
Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath

Write-Host "[info] Extracting files..." -ForegroundColor Green
Expand-Archive -Path $ZipPath -DestinationPath $InstallDir -Force
Remove-Item $ZipPath

# Configure environment PATH (Persistent User environment)
Write-Host "[info] Configuring PATH environment variable..." -ForegroundColor Green
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$InstallDir*") {
    $NewPath = $UserPath
    if ($NewPath -and -not $NewPath.EndsWith(";")) {
        $NewPath += ";"
    }
    $NewPath += $InstallDir
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    
    # Update current session path
    $env:PATH = "$env:PATH;$InstallDir"
    
    Write-Host "[info] Added $InstallDir to your User PATH." -ForegroundColor Green
    Write-Host "[warn] Please restart your terminal/PowerShell session to apply PATH changes." -ForegroundColor Yellow
} else {
    Write-Host "[info] VinylKit bin directory is already in your PATH." -ForegroundColor Green
}

Write-Host "[info] VinylKit installed successfully!" -ForegroundColor Green
& (Join-Path $InstallDir "vinylkit.exe") --version
