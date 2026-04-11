"""
Tests for music_analyzer.camelot — Camelot wheel logic.
"""

from excalibpm.camelot import (
    _circular_distance,
    compatibility,
    get_camelot,
    get_openkey,
    suggest_next,
)


# ── get_camelot ──────────────────────────────────────────────────────────────

class TestGetCamelot:
    def test_c_major(self):
        assert get_camelot("C Major") == "8B"

    def test_a_minor(self):
        assert get_camelot("A Minor") == "8A"

    def test_f_sharp_major(self):
        assert get_camelot("F# Major") == "2B"

    def test_unknown_key_returns_none(self):
        assert get_camelot("X Unknown") is None

    def test_all_24_keys_mapped(self):
        from excalibpm.camelot import KEY_TO_CAMELOT
        assert len(KEY_TO_CAMELOT) == 24


# ── get_openkey ──────────────────────────────────────────────────────────────

class TestGetOpenkey:
    def test_c_major(self):
        assert get_openkey("C Major") == "1d"

    def test_a_minor(self):
        assert get_openkey("A Minor") == "1m"

    def test_unknown_key_returns_none(self):
        assert get_openkey("Xpto") is None

    def test_all_24_keys_mapped(self):
        from excalibpm.camelot import KEY_TO_OPENKEY
        assert len(KEY_TO_OPENKEY) == 24


# ── _circular_distance ───────────────────────────────────────────────────────

class TestCircularDistance:
    def test_same_numbers(self):
        assert _circular_distance(5, 5) == 0

    def test_neighbors(self):
        assert _circular_distance(1, 2) == 1
        assert _circular_distance(12, 11) == 1

    def test_maximum_distance_is_six(self):
        assert _circular_distance(1, 7) == 6

    def test_wraparound(self):
        # 12 and 1 are neighbors on the wheel (distance 1)
        assert _circular_distance(12, 1) == 1

    def test_symmetry(self):
        assert _circular_distance(3, 8) == _circular_distance(8, 3)


# ── compatibility ────────────────────────────────────────────────────────────

class TestCompatibility:
    def test_same_key_is_perfect(self):
        r = compatibility("C Major", "C Major")
        assert r["level"] == "perfect"
        assert r["distance"] == 0

    def test_relative_major_minor_is_perfect(self):
        # C Major (8B) and A Minor (8A) — same number, different letter
        r = compatibility("C Major", "A Minor")
        assert r["level"] == "perfect"
        assert "relative" in r["description"].lower()

    def test_same_letter_neighbor_is_good(self):
        # G Major (9B) is a neighbor of C Major (8B)
        r = compatibility("C Major", "G Major")
        assert r["level"] == "good"
        assert r["distance"] == 1

    def test_cross_neighbor_is_good(self):
        # C Major (8B) and E Minor (9A): dist=1, different letters
        r = compatibility("C Major", "E Minor")
        assert r["level"] == "good"
        assert r["distance"] == 1

    def test_distance_2_is_risky(self):
        # C Major (8B) and D Major (10B): dist=2
        r = compatibility("C Major", "D Major")
        assert r["level"] == "risky"
        assert r["distance"] == 2

    def test_incompatible_keys(self):
        # C Major (8B) and F# Major (2B): dist=6 — opposite on wheel
        r = compatibility("C Major", "F# Major")
        assert r["level"] == "incompatible"

    def test_unknown_key_returns_unknown_level(self):
        r = compatibility("X Unknown", "C Major")
        assert r["level"] == "unknown"
        assert r["distance"] == -1

    def test_camelot_codes_are_correct(self):
        r = compatibility("C Major", "G Major")
        assert r["camelot_a"] == "8B"
        assert r["camelot_b"] == "9B"

    def test_known_valid_keys_never_raise(self):
        r = compatibility("C Major", "C Major")
        assert r is not None


# ── suggest_next ─────────────────────────────────────────────────────────────

class TestSuggestNext:
    def test_returns_non_empty_list_for_valid_key(self):
        suggestions = suggest_next("C Major")
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_returns_empty_list_for_unknown_key(self):
        assert suggest_next("Unknown Key") == []

    def test_suggestions_have_required_fields(self):
        suggestions = suggest_next("A Minor")
        for s in suggestions:
            assert "key" in s
            assert "camelot" in s
            assert "level" in s
            assert "description" in s

    def test_relative_key_is_in_suggestions(self):
        # Relative of C Major is A Minor
        suggestions = suggest_next("C Major")
        keys = [s["key"] for s in suggestions]
        assert "A Minor" in keys

    def test_wheel_neighbors_are_in_suggestions(self):
        # Neighbors of C Major (8B): G Major (9B) and F Major (7B)
        suggestions = suggest_next("C Major")
        keys = [s["key"] for s in suggestions]
        assert "G Major" in keys
        assert "F Major" in keys

    def test_perfect_and_good_levels_present(self):
        suggestions = suggest_next("C Major")
        levels = {s["level"] for s in suggestions}
        assert "perfect" in levels
        assert "good" in levels
