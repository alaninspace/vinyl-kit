"""Tests for scripts/update_hashes.py (release checksum updates)."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

_SCRIPT = Path(__file__).parent.parent / "scripts" / "update_hashes.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("update_hashes", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_FORMULA = """\
    if Hardware::CPU.arm?
      url "https://example.com/download/v1.0.0/vinylkit-macos-arm64.zip"
      sha256 "{mac}"
    end
  elsif OS.linux?
    url "https://example.com/download/v1.0.0/vinylkit-linux-amd64.tar.gz"
    sha256 "{linux}"
  end
"""

_NEW = {
    "vinylkit-macos-arm64.zip": "a" * 64,
    "vinylkit-linux-amd64.tar.gz": "b" * 64,
}


@pytest.mark.parametrize(
    ("mac", "linux"),
    [
        ("PLACEHOLDER_MAC_ARM64", "PLACEHOLDER_LINUX_AMD64"),
        ("1" * 64, "2" * 64),  # previous release's checksums
    ],
)
def test_update_formula_replaces_checksums(mac: str, linux: str) -> None:
    """Checksums are rewritten whether they are placeholders or stale values."""
    module = _load_script()
    updated = module.update_formula(_FORMULA.format(mac=mac, linux=linux), _NEW)
    assert updated == _FORMULA.format(mac="a" * 64, linux="b" * 64)


def test_update_formula_errors_when_url_missing() -> None:
    """A formula without the expected URL fails loudly instead of skipping."""
    module = _load_script()
    with pytest.raises(ValueError, match=re.escape("vinylkit-linux-amd64.tar.gz")):
        module.update_formula('url "x/vinylkit-macos-arm64.zip"\nsha256 "0"\n', _NEW)


def test_repo_formula_is_updatable() -> None:
    """The real formula keeps the url/sha256 layout the script depends on."""
    module = _load_script()
    formula = (Path(__file__).parent.parent / "Formula" / "vinyl-kit.rb").read_text(
        encoding="utf-8"
    )
    updated = module.update_formula(formula, _NEW)
    assert 'sha256 "' + "a" * 64 + '"' in updated
    assert 'sha256 "' + "b" * 64 + '"' in updated
