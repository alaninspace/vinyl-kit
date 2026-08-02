"""Tests for shared helpers in vinylkit.commands._helpers."""

from __future__ import annotations

from vinylkit.commands._helpers import (
    extract_id,
    is_low_quality_text_match,
    parse_folder_search_query,
)


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


class TestParseFolderSearchQuery:
    def test_trailing_parens_catno_and_and_normalization(self) -> None:
        q = parse_folder_search_query(
            "M_And_M-I_Feel_This_Way__Don't_Stand_In_My_Way_(Remixes)-(SUB_BASE_006R)"
        )
        assert q.catno == "SUB BASE 006R"
        assert q.cleaned_query == "M & M I Feel This Way Don't Stand In My Way Remixes"

    def test_trailing_parens_catno_simple(self) -> None:
        q = parse_folder_search_query("Manix-Bad_Attitude-(Remixes)-(RIVET_1212R)")
        assert q.catno == "RIVET 1212R"
        assert q.cleaned_query == "Manix Bad Attitude Remixes"

    def test_catno_with_dots_and_ep(self) -> None:
        q = parse_folder_search_query("M.A.D-Katalystik_EP-(dfd24)")
        assert q.catno == "dfd24"
        assert q.cleaned_query == "M A D Katalystik EP"

    def test_scene_style_catno(self) -> None:
        q = parse_folder_search_query(
            "Noise_Factory-Generation_X-Vinyl-3RD#6-FLAC-1993"
        )
        assert q.catno == "3RD#6"

    def test_no_catno_folder(self) -> None:
        q = parse_folder_search_query("Under The Influence - Lost In Music")
        assert q.catno is None
        assert q.cleaned_query == "Under The Influence Lost In Music"


class TestIsLowQualityTextMatch:
    def test_detects_various_artist_mismatch(self) -> None:
        q = parse_folder_search_query("Miranda-Volume_Two-(HAN013)")
        results = [{"id": 3062416, "title": "Various - European Edition Volume Two"}]
        assert is_low_quality_text_match(results, q) is True

    def test_accepts_good_artist_match(self) -> None:
        q = parse_folder_search_query("Manix-Rainbow_People-(RIVET_1221)")
        results = [{"id": 1185, "title": "Manix - Rainbow People"}]
        assert is_low_quality_text_match(results, q) is False
