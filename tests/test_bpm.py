"""
Tests for music_analyzer.bpm — BPM detection.

Integration tests that require real audio are marked with
@pytest.mark.integration and can be skipped via: pytest -m "not integration"
The remaining tests cover normalization logic and edge cases.
"""

import numpy as np

from excalibpm.bpm import detect_bpm


class TestDetectBpmNormalization:
    """Verify the normalization logic for the 60-180 BPM range."""

    def test_returns_float(self):
        signal = np.zeros(22050)
        assert isinstance(detect_bpm(signal, sr=22050), float)

    def test_result_never_below_60(self):
        rng = np.random.default_rng(7)
        signal = rng.standard_normal(22050 * 5).astype(np.float32)
        bpm = detect_bpm(signal, sr=22050)
        if bpm > 0:
            assert bpm >= 60.0

    def test_result_never_above_180(self):
        rng = np.random.default_rng(13)
        signal = rng.standard_normal(22050 * 5).astype(np.float32)
        bpm = detect_bpm(signal, sr=22050)
        if bpm > 0:
            assert bpm <= 180.0

    def test_percussive_signal_is_preferred_over_original(self):
        """When y_percussive is provided, detect_bpm must use it."""
        y = np.zeros(22050 * 3)
        sr = 22050
        # Percussive signal with pulses at ~120 BPM
        interval = int(sr * 60 / 120)
        percussive = np.zeros(sr * 3)
        for i in range(0, len(percussive), interval):
            percussive[i] = 1.0

        bpm = detect_bpm(y, sr=sr, y_percussive=percussive)
        assert isinstance(bpm, float)
        assert bpm >= 60.0

    def test_silent_signal_returns_zero_or_float(self):
        signal = np.zeros(22050 * 2)
        assert isinstance(detect_bpm(signal, sr=22050), float)
