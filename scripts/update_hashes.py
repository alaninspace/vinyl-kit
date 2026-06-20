#!/usr/bin/env python3
"""Calculates SHA256 checksums of build artifacts and updates package manager files."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def get_sha256(filepath: Path) -> str:
    """Calculate the SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with filepath.open("rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def main() -> int:
    artifacts_dir = Path("all-artifacts")
    formula_path = Path("Formula/vinyl-kit.rb")
    scoop_path = Path("scoop/vinylkit.json")

    if not artifacts_dir.exists():
        print(
            f"Error: Artifacts directory '{artifacts_dir}' not found.",
            file=sys.stderr,
        )
        return 1

    # Map target filenames to their respective paths
    file_map = {
        "mac_arm64": artifacts_dir / "vinylkit-macos-arm64.zip",
        "linux_amd64": artifacts_dir / "vinylkit-linux-amd64.tar.gz",
        "win_amd64": artifacts_dir / "vinylkit-windows-amd64.zip",
    }

    # Verify all files exist
    hashes: dict[str, str] = {}
    for key, path in file_map.items():
        if not path.exists():
            print(f"Error: Required artifact '{path}' is missing.", file=sys.stderr)
            return 1
        hashes[key] = get_sha256(path)
        print(f"Calculated {key} hash: {hashes[key]}")

    # 1. Update Homebrew Formula (Formula/vinyl-kit.rb)
    if formula_path.exists():
        content = formula_path.read_text(encoding="utf-8")

        # Replace placeholders
        content = content.replace("PLACEHOLDER_MAC_ARM64", hashes["mac_arm64"])
        content = content.replace("PLACEHOLDER_LINUX_AMD64", hashes["linux_amd64"])

        formula_path.write_text(content, encoding="utf-8")
        print("Updated Homebrew formula checksums successfully.")
    else:
        print("Warning: Homebrew formula file not found.", file=sys.stderr)

    # 2. Update Scoop Manifest (scoop/vinylkit.json)
    if scoop_path.exists():
        with scoop_path.open("r", encoding="utf-8") as f:
            scoop_data = json.load(f)

        # Update the hash
        scoop_data["hash"] = hashes["win_amd64"]

        with scoop_path.open("w", encoding="utf-8") as f:
            json.dump(scoop_data, f, indent=2)
            f.write("\n")  # Ensure trailing newline
        print("Updated Scoop manifest checksum successfully.")
    else:
        print("Warning: Scoop manifest file not found.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
