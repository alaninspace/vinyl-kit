"""Tests to ensure version strings are synchronized across all configuration files."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path


def test_versions_are_synchronized() -> None:
    """Verify that pyproject.toml, Homebrew, and Scoop versions are in sync."""
    root_dir = Path(__file__).parent.parent

    # 1. Read master version from pyproject.toml
    pyproject_path = root_dir / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml does not exist"
    with pyproject_path.open("rb") as f:
        pyproject_data = tomllib.load(f)
    master_version = pyproject_data.get("project", {}).get("version")
    assert master_version, "Could not find version in pyproject.toml"

    # 2. Verify Homebrew Formula (Formula/vinyl-kit.rb)
    formula_path = root_dir / "Formula" / "vinyl-kit.rb"
    assert formula_path.exists(), "Homebrew formula does not exist"
    formula_content = formula_path.read_text(encoding="utf-8")

    # Extract version "0.13.11"
    formula_ver_match = re.search(r'version\s+"([^"]+)"', formula_content)
    assert formula_ver_match, "Could not find version declaration in Homebrew formula"
    formula_version = formula_ver_match.group(1)

    assert formula_version == master_version, (
        f"Homebrew formula version ({formula_version}) "
        f"does not match pyproject.toml version ({master_version})"
    )

    # Ensure all download URLs in Formula match the master version
    url_version_pattern = rf"releases/download/v{re.escape(master_version)}/"
    urls_in_formula = re.findall(r'url\s+"([^"]+)"', formula_content)
    assert urls_in_formula, "Could not find any download URLs in Homebrew formula"
    for url in urls_in_formula:
        assert re.search(url_version_pattern, url), (
            f"Homebrew formula URL ({url}) "
            f"does not reference the correct release version v{master_version}"
        )

    # 3. Verify Scoop Manifest (scoop/vinylkit.json)
    scoop_path = root_dir / "scoop" / "vinylkit.json"
    assert scoop_path.exists(), "Scoop manifest does not exist"
    with scoop_path.open("r", encoding="utf-8") as f:
        scoop_data = json.load(f)

    scoop_version = scoop_data.get("version")
    assert scoop_version == master_version, (
        f"Scoop manifest version ({scoop_version}) "
        f"does not match pyproject.toml version ({master_version})"
    )

    # Ensure Scoop URLs match the master version
    scoop_url = scoop_data.get("url")
    assert scoop_url, "Could not find download URL in Scoop manifest"
    assert re.search(url_version_pattern, scoop_url), (
        f"Scoop download URL ({scoop_url}) "
        f"does not reference the correct release version v{master_version}"
    )

    scoop_autoupdate_url = scoop_data.get("autoupdate", {}).get("url")
    assert scoop_autoupdate_url, "Could not find autoupdate URL in Scoop manifest"
    assert "v$version/" in scoop_autoupdate_url, (
        f"Scoop autoupdate URL ({scoop_autoupdate_url}) "
        f"should reference v$version/ dynamically"
    )
