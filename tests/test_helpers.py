"""Tests for shared helpers in vinylkit.commands._helpers."""

from __future__ import annotations

from vinylkit.commands._helpers import extract_id


class TestExtractId:
    def test_bracket_suffix(self) -> None:
        assert extract_id("Artist - Album [12345]") == 12345

    def test_bare_numeric(self) -> None:
        assert extract_id("67890") == 67890

    def test_no_match(self) -> None:
        assert extract_id("Some Folder") is None

    def test_bracket_not_at_end(self) -> None:
        assert extract_id("[123] Artist") is None

    def test_zero_id_returns_none(self) -> None:
        assert extract_id("Artist [0]") is None

    def test_bare_zero_returns_none(self) -> None:
        assert extract_id("0") is None

    def test_url_style_prefix(self) -> None:
        assert extract_id("50224-Breeder-New-York-FM-Rockstone") == 50224

    def test_url_style_prefix_longer_id(self) -> None:
        assert extract_id("178842-Sub-Urbans-Feel-Your-Soul") == 178842

    def test_url_style_zero_returns_none(self) -> None:
        assert extract_id("0-Some-Artist") is None
