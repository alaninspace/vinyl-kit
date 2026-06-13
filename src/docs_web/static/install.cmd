@echo off
rem VinylKit Installer for Windows CMD
rem Delegates execution to PowerShell script

echo [info] Launching PowerShell installation script...
powershell -NoProfile -ExecutionPolicy Bypass -Command "iex (irm https://vinylkit.app/install.ps1)"
