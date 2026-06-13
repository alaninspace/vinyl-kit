#!/usr/bin/env bash

# VinylKit Installer for macOS and Linux
# Installs standalone binary to ~/.vinylkit/bin

set -euo pipefail

# Echo utilities
info() { echo -e "\033[0;32m[info]\033[0m $*"; }
warn() { echo -e "\033[0;33m[warn]\033[0m $*"; }
error() { echo -e "\033[0;31m[error]\033[0m $*"; exit 1; }

# Determine OS and Architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

info "Detecting platform: $OS ($ARCH)"

case "$OS" in
    Darwin)
        if [ "$ARCH" = "arm64" ]; then
            FILENAME="vinylkit-macos-arm64.zip"
        else
            FILENAME="vinylkit-macos-x86_64.zip"
        fi
        ;;
    Linux)
        if [ "$ARCH" = "x86_64" ]; then
            FILENAME="vinylkit-linux-amd64.tar.gz"
        else
            error "Unsupported architecture $ARCH for Linux. We currently only release x86_64 binaries."
        fi
        ;;
    *)
        error "Unsupported operating system: $OS"
        ;;
esac

INSTALL_DIR="$HOME/.vinylkit/bin"
info "Installing to: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Download URL
DOWNLOAD_URL="https://github.com/alaninspace/vinyl-kit/releases/latest/download/$FILENAME"
TEMP_FILE="$(mktemp -t vinylkit-install-XXXXXX)"

info "Downloading latest release..."
if command -v curl >/dev/null; then
    curl -fsSL "$DOWNLOAD_URL" -o "$TEMP_FILE"
elif command -v wget >/dev/null; then
    wget -qO "$TEMP_FILE" "$DOWNLOAD_URL"
else
    error "Could not find curl or wget. Please install one of them to download VinylKit."
fi

# Extract
info "Extracting binary..."
if [[ "$FILENAME" == *.zip ]]; then
    if ! command -v unzip >/dev/null; then
        error "unzip command not found. Please install unzip to continue."
    fi
    unzip -oq "$TEMP_FILE" -d "$INSTALL_DIR"
else
    tar -xzf "$TEMP_FILE" -C "$INSTALL_DIR"
fi
rm -f "$TEMP_FILE"

# Set permissions
chmod +x "$INSTALL_DIR/vinylkit"

# Bypass macOS Gatekeeper Quarantine
if [ "$OS" = "Darwin" ]; then
    info "Stripping macOS Gatekeeper quarantine flags..."
    xattr -d com.apple.quarantine "$INSTALL_DIR/vinylkit" 2>/dev/null || true
fi

# Detect Shell Profile
SHELL_NAME="$(basename "$SHELL")"
SHELL_RC=""

case "$SHELL_NAME" in
    zsh)
        SHELL_RC="$HOME/.zshrc"
        ;;
    bash)
        if [ -f "$HOME/.bash_profile" ]; then
            SHELL_RC="$HOME/.bash_profile"
        else
            SHELL_RC="$HOME/.bashrc"
        fi
        ;;
    *)
        if [ -f "$HOME/.profile" ]; then
            SHELL_RC="$HOME/.profile"
        fi
        ;;
esac

EXPORT_LINE='export PATH="$HOME/.vinylkit/bin:$PATH"'

# Configure PATH
if [ -n "$SHELL_RC" ]; then
    if [ -f "$SHELL_RC" ] && grep -q ".vinylkit/bin" "$SHELL_RC"; then
        info "VinylKit bin directory is already in your PATH ($SHELL_RC)."
    else
        info "Adding ~/.vinylkit/bin to your PATH in $SHELL_RC..."
        echo "" >> "$SHELL_RC"
        echo "# VinylKit CLI path adjustment" >> "$SHELL_RC"
        echo "$EXPORT_LINE" >> "$SHELL_RC"
        warn "Please run: source $SHELL_RC (or restart your terminal) to apply the change."
    fi
else
    warn "Could not determine shell configuration file. Please manually add $INSTALL_DIR to your PATH:"
    echo "  export PATH=\"\$PATH:$INSTALL_DIR\""
fi

info "VinylKit installed successfully!"
"$INSTALL_DIR/vinylkit" --version || true
