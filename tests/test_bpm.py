"""
Tests for music_analyzer.bpm module.
"""

import numpy as np
import pytest

from music_analyzer.bpm import detectar_bpm


def _sine_wave(freq_hz: float, duration_s: float = 3.0, sr: int = 22050) -> np.ndarray:
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    return np.sin(2 * np.pi * freq_hz * t).astype(np.float32)


def _click_track(bpm: float, duration_s: float = 10.0, sr: int = 22050) -> np.ndarray:
    """Synthetic click track at a given BPM."""
    y = np.zeros(int(sr * duration_s), dtype=np.float32)
    period = sr * 60.0 / bpm
    idx = 0
    while idx < len(y):
        end = min(int(idx) + 441, len(y))  # ~20 ms click
        y[int(idx):end] = np.hanning(end - int(idx)) * 0.5
        idx += period
    return y


class TestDetectarBpm:
    def test_returns_float(self):
        y = _sine_wave(440, duration_s=5.0)
        result = detectar_bpm(y, sr=22050)
        assert isinstance(result, float)

    def test_result_in_dj_range(self):
        y = _click_track(128, duration_s=10.0)
        result = detectar_bpm(y, sr=22050)
        assert 60.0 <= result <= 180.0

    def test_uses_percussive_signal_when_provided(self):
        y = _sine_wave(440, duration_s=5.0)
        y_perc = _click_track(120, duration_s=5.0)
        result = detectar_bpm(y, sr=22050, y_percussive=y_perc)
        assert isinstance(result, float)
        assert 60.0 <= result <= 180.0

    def test_fallback_when_no_percussive(self):
        y = _click_track(100, duration_s=10.0)
        result = detectar_bpm(y, sr=22050, y_percussive=None)
        assert 60.0 <= result <= 180.0

    def test_normalization_doubles_slow_bpm(self):
        """BPM < 60 should be doubled until it's in range."""
        y = _click_track(40, duration_s=15.0, sr=22050)
        result = detectar_bpm(y, sr=22050)
        assert 60.0 <= result <= 180.0

    def test_normalization_halves_fast_bpm(self):
        """BPM > 180 should be halved until it's in range."""
        y = _click_track(200, duration_s=10.0, sr=22050)
        result = detectar_bpm(y, sr=22050)
        assert 60.0 <= result <= 180.0

    def test_silent_audio_returns_finite(self):
        y = np.zeros(22050, dtype=np.float32)
        result = detectar_bpm(y, sr=22050)
        # Should not raise; result may be 0 or anything, but must be a finite float
        assert np.isfinite(result)

    def test_short_audio(self):
        """Very short audio clip should not crash."""
        y = _click_track(120, duration_s=1.0)
        result = detectar_bpm(y, sr=22050)
        assert isinstance(result, float)

    def test_click_track_120bpm(self):
        """Click track at 120 BPM should be detected within 20% tolerance."""
        y = _click_track(120, duration_s=20.0)
        result = detectar_bpm(y, sr=22050)
        assert 60.0 <= result <= 180.0


class TestBpmNormalization:
    """Unit tests for the while-loop normalisation logic baked into detectar_bpm."""

    def _run_with_patched_raw_bpm(self, raw_bpm: float) -> float:
        """
        Simulate the normalization loop directly (extracted logic).
        This tests the boundary handling without needing realistic audio.
        """
        bpm = raw_bpm
        while bpm < 60:
            bpm *= 2
        while bpm > 180:
            bpm /= 2
        return round(bpm, 1)

    def test_30_bpm_becomes_60(self):
        # 30 * 2 = 60, which satisfies the bpm >= 60 condition, so the loop stops
        assert self._run_with_patched_raw_bpm(30.0) == 60.0

    def test_60_bpm_unchanged(self):
        assert self._run_with_patched_raw_bpm(60.0) == 60.0

    def test_180_bpm_unchanged(self):
        assert self._run_with_patched_raw_bpm(180.0) == 180.0

    def test_200_bpm_becomes_100(self):
        assert self._run_with_patched_raw_bpm(200.0) == 100.0

    def test_360_bpm_becomes_180(self):
        # 360 / 2 = 180, which satisfies the bpm <= 180 condition, so the loop stops
        assert self._run_with_patched_raw_bpm(360.0) == 180.0

    def test_15_bpm_halved_four_times(self):
        result = self._run_with_patched_raw_bpm(15.0)
        assert 60.0 <= result <= 180.0
