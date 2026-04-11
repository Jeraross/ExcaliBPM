"""
Tests for music_analyzer.key_detect — key detection engine.
"""

import numpy as np

from excalibpm.key_detect import (
    KeyResult,
    _euclidean_similarity,
    _pearson_correlation,
    disambiguate_result,
    detect_with_profile,
    ensemble_vote,
    frame_vote,
)
from excalibpm.profiles import get_all_profiles


# ── _pearson_correlation ─────────────────────────────────────────────────────

class TestPearsonCorrelation:
    def test_perfect_correlation(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        assert abs(_pearson_correlation(x, x) - 1.0) < 1e-9

    def test_perfect_negative_correlation(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        assert abs(_pearson_correlation(x, -x) + 1.0) < 1e-9

    def test_zero_vector_returns_zero(self):
        x = np.zeros(12)
        y = np.array([1.0] * 12)
        assert _pearson_correlation(x, y) == 0.0

    def test_result_between_minus1_and_1(self):
        rng = np.random.default_rng(42)
        for _ in range(20):
            x = rng.random(12)
            y = rng.random(12)
            r = _pearson_correlation(x, y)
            assert -1.0 - 1e-9 <= r <= 1.0 + 1e-9


# ── _euclidean_similarity ────────────────────────────────────────────────────

class TestEuclideanSimilarity:
    def test_identical_vector_returns_1(self):
        x = np.array([1.0, 0.5, 0.3, 0.8, 0.2, 0.1, 0.0, 0.9, 0.4, 0.6, 0.1, 0.3])
        assert abs(_euclidean_similarity(x, x) - 1.0) < 1e-9

    def test_result_is_positive(self):
        rng = np.random.default_rng(0)
        x, y = rng.random(12), rng.random(12)
        assert _euclidean_similarity(x, y) > 0

    def test_result_at_most_1(self):
        rng = np.random.default_rng(1)
        x, y = rng.random(12), rng.random(12)
        assert _euclidean_similarity(x, y) <= 1.0 + 1e-9

    def test_zero_vector_does_not_raise(self):
        x = np.zeros(12)
        y = np.ones(12)
        assert np.isfinite(_euclidean_similarity(x, y))


# ── detect_with_profile ──────────────────────────────────────────────────────

class TestDetectWithProfile:
    def test_returns_triple(self, chroma_c_major):
        p = get_all_profiles()["bellman_budge"]
        assert len(detect_with_profile(chroma_c_major, p["major"], p["minor"])) == 3

    def test_returned_key_is_valid_string(self, chroma_c_major):
        p = get_all_profiles()["bellman_budge"]
        key, _, _ = detect_with_profile(chroma_c_major, p["major"], p["minor"])
        assert isinstance(key, str)
        assert "Major" in key or "Minor" in key

    def test_confidence_between_0_and_1(self, chroma_c_major):
        p = get_all_profiles()["bellman_budge"]
        _, confidence, _ = detect_with_profile(chroma_c_major, p["major"], p["minor"])
        assert 0.0 <= confidence <= 1.0

    def test_correlations_has_24_entries(self, chroma_c_major):
        p = get_all_profiles()["bellman_budge"]
        _, _, corrs = detect_with_profile(chroma_c_major, p["major"], p["minor"])
        assert len(corrs) == 24

    def test_c_major_chroma_detects_c_major(self, chroma_c_major):
        p = get_all_profiles()["bellman_budge"]
        key, _, _ = detect_with_profile(chroma_c_major, p["major"], p["minor"])
        assert key == "C Major"

    def test_euclidean_mode_does_not_raise(self, chroma_c_major):
        p = get_all_profiles()["albrecht_shanahan"]
        key, confidence, _ = detect_with_profile(
            chroma_c_major, p["major"], p["minor"], use_euclidean=True
        )
        assert isinstance(key, str)
        assert 0.0 <= confidence <= 1.0


# ── ensemble_vote ────────────────────────────────────────────────────────────

class TestEnsembleVote:
    def test_returns_key_result(self, chroma_c_major):
        assert isinstance(ensemble_vote(chroma_c_major), KeyResult)

    def test_confidence_between_0_and_1(self, chroma_c_major):
        assert 0.0 <= ensemble_vote(chroma_c_major).confidence <= 1.0

    def test_profile_votes_populated(self, chroma_c_major):
        assert len(ensemble_vote(chroma_c_major).profile_votes) > 0

    def test_c_major_chroma_wins_with_c_major(self, chroma_c_major):
        assert ensemble_vote(chroma_c_major).key == "C Major"

    def test_g_major_chroma_detects_g_major(self, chroma_g_major):
        assert ensemble_vote(chroma_g_major).key == "G Major"

    def test_custom_profiles_are_used(self, chroma_c_major):
        profiles = {"bellman_budge": get_all_profiles()["bellman_budge"]}
        r = ensemble_vote(chroma_c_major, profiles=profiles)
        assert len(r.profile_votes) == 1


# ── frame_vote ───────────────────────────────────────────────────────────────

class TestFrameVote:
    def test_returns_key_result(self, chroma_matrix_c_major):
        assert isinstance(frame_vote(chroma_matrix_c_major, sr=22050), KeyResult)

    def test_frame_votes_populated(self, chroma_matrix_c_major):
        r = frame_vote(chroma_matrix_c_major, sr=22050)
        assert r.frame_votes is not None
        assert len(r.frame_votes) > 0

    def test_c_major_chroma_detects_c_major(self, chroma_matrix_c_major):
        assert frame_vote(chroma_matrix_c_major, sr=22050).key == "C Major"

    def test_confidence_between_0_and_1(self, chroma_matrix_c_major):
        assert 0.0 <= frame_vote(chroma_matrix_c_major, sr=22050).confidence <= 1.0

    def test_zero_matrix_returns_undetermined(self):
        r = frame_vote(np.zeros((12, 50)), sr=22050)
        assert r.key == "Undetermined"
        assert r.confidence == 0.0

    def test_silence_filter_works(self, chroma_matrix_c_major):
        # Zero RMS should filter all frames → Undetermined
        rms_zero = np.zeros(chroma_matrix_c_major.shape[1])
        r = frame_vote(chroma_matrix_c_major, sr=22050, rms=rms_zero)
        assert r.key == "Undetermined"


# ── disambiguate_result ──────────────────────────────────────────────────────

class TestDisambiguateResult:
    def _make_result(self, key: str, confidence: float = 0.8) -> KeyResult:
        return KeyResult(key=key, confidence=confidence, correlations={}, profile_votes={})

    def test_returns_key_result(self):
        r = self._make_result("C Major")
        assert isinstance(disambiguate_result(r, r, r, r), KeyResult)

    def test_full_consensus_returns_correct_key(self):
        r = self._make_result("G Major")
        assert disambiguate_result(r, r, r, r).key == "G Major"

    def test_confidence_between_0_and_1(self):
        r = self._make_result("D Minor")
        assert 0.0 <= disambiguate_result(r, r, r, r).confidence <= 1.0

    def test_no_bass_does_not_raise(self):
        r = self._make_result("A Minor")
        assert disambiguate_result(r, r, r, r, bass_chroma=None).key == "A Minor"

    def test_disambiguation_with_bass(self):
        # Conflict: global and frames vote C Major, end votes A Minor
        r_global = self._make_result("C Major")
        r_frames = self._make_result("C Major")
        r_start = self._make_result("C Major")
        r_end = self._make_result("A Minor")

        # Bass heavily on C (index 0)
        bass_chroma = np.zeros((12, 10))
        bass_chroma[0] = 5.0

        result = disambiguate_result(r_global, r_frames, r_start, r_end, bass_chroma)
        # C Major has more weighted votes (3+3+1=7 vs 2)
        assert result.key == "C Major"
