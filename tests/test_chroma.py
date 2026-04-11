"""
Tests for music_analyzer.chroma module.
"""

import numpy as np
import pytest

from music_analyzer.chroma import (
    extrair_harmonico,
    estimar_afinacao,
    extrair_chroma_cqt,
    extrair_chroma_cens,
    filtrar_chroma,
    ponderar_por_energia,
    pipeline_chroma,
)


SR = 22050
DURATION = 3.0  # seconds — long enough for CQT filters


@pytest.fixture(scope="module")
def sine_audio():
    """3-second 440 Hz (A4) sine wave."""
    t = np.linspace(0, DURATION, int(SR * DURATION), endpoint=False)
    y = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
    return y, SR


@pytest.fixture(scope="module")
def chord_audio():
    """3-second C-major triad (C4=261.63, E4=329.63, G4=392 Hz)."""
    n = int(SR * DURATION)
    t = np.linspace(0, DURATION, n, endpoint=False)
    y = (
        np.sin(2 * np.pi * 261.63 * t) +
        np.sin(2 * np.pi * 329.63 * t) +
        np.sin(2 * np.pi * 392.00 * t)
    ).astype(np.float32) / 3.0
    return y, SR


class TestExtrairHarmonico:
    def test_returns_ndarray(self, sine_audio):
        y, sr = sine_audio
        result = extrair_harmonico(y)
        assert isinstance(result, np.ndarray)

    def test_output_same_length_as_input(self, sine_audio):
        y, sr = sine_audio
        result = extrair_harmonico(y)
        assert result.shape == y.shape

    def test_output_is_finite(self, sine_audio):
        y, sr = sine_audio
        result = extrair_harmonico(y)
        assert np.all(np.isfinite(result))

    def test_custom_margin(self, sine_audio):
        y, sr = sine_audio
        result = extrair_harmonico(y, margin=4)
        assert result.shape == y.shape


class TestEstimarAfinacao:
    def test_returns_float(self, sine_audio):
        y, sr = sine_audio
        result = estimar_afinacao(y, sr)
        assert isinstance(result, float)

    def test_result_in_cents_range(self, sine_audio):
        y, sr = sine_audio
        result = estimar_afinacao(y, sr)
        # Typical range is [-0.5, 0.5] semitone
        assert -1.0 <= result <= 1.0


class TestExtrairChromaCqt:
    def test_returns_ndarray(self, chord_audio):
        y, sr = chord_audio
        result = extrair_chroma_cqt(y, sr)
        assert isinstance(result, np.ndarray)

    def test_output_has_12_rows(self, chord_audio):
        y, sr = chord_audio
        result = extrair_chroma_cqt(y, sr)
        assert result.shape[0] == 12

    def test_output_is_non_negative(self, chord_audio):
        y, sr = chord_audio
        result = extrair_chroma_cqt(y, sr)
        assert np.all(result >= -1e-10)

    def test_custom_tuning(self, chord_audio):
        y, sr = chord_audio
        result = extrair_chroma_cqt(y, sr, tuning=0.0)
        assert result.shape[0] == 12

    def test_c_major_prominent_in_chroma(self, chord_audio):
        """C, E, G should dominate the chroma vector."""
        y, sr = chord_audio
        chroma = extrair_chroma_cqt(y, sr)
        mean_chroma = np.mean(chroma, axis=1)
        # C=0, E=4, G=7
        top3 = set(np.argsort(mean_chroma)[-3:])
        assert top3.intersection({0, 4, 7})


class TestExtrairChromaCens:
    def test_returns_ndarray(self, chord_audio):
        y, sr = chord_audio
        result = extrair_chroma_cens(y, sr)
        assert isinstance(result, np.ndarray)

    def test_output_has_12_rows(self, chord_audio):
        y, sr = chord_audio
        result = extrair_chroma_cens(y, sr)
        assert result.shape[0] == 12

    def test_output_is_non_negative(self, chord_audio):
        y, sr = chord_audio
        result = extrair_chroma_cens(y, sr)
        assert np.all(result >= -1e-10)


class TestFiltrarChroma:
    def test_returns_ndarray(self):
        chroma = np.random.default_rng(0).random((12, 100))
        result = filtrar_chroma(chroma)
        assert isinstance(result, np.ndarray)

    def test_output_same_shape(self):
        chroma = np.random.default_rng(1).random((12, 80))
        result = filtrar_chroma(chroma)
        assert result.shape == chroma.shape

    def test_values_are_non_negative(self):
        """After filtering, values should not be negative."""
        chroma = np.abs(np.random.default_rng(2).random((12, 50)))
        result = filtrar_chroma(chroma)
        assert np.all(result >= -1e-10)


class TestPonderarPorEnergia:
    def test_returns_ndarray(self, sine_audio):
        y, sr = sine_audio
        chroma = np.ones((12, 100))
        result = ponderar_por_energia(chroma, y, sr)
        assert isinstance(result, np.ndarray)

    def test_output_has_12_rows(self, sine_audio):
        y, sr = sine_audio
        chroma = np.ones((12, 100))
        result = ponderar_por_energia(chroma, y, sr)
        assert result.shape[0] == 12

    def test_silent_audio_gives_near_zero(self):
        y = np.zeros(SR * 2, dtype=np.float32)
        chroma = np.ones((12, 100))
        result = ponderar_por_energia(chroma, y, SR)
        assert np.all(result < 1e-5)

    def test_output_is_finite(self, sine_audio):
        y, sr = sine_audio
        chroma = np.abs(np.random.default_rng(4).random((12, 150)))
        result = ponderar_por_energia(chroma, y, sr)
        assert np.all(np.isfinite(result))


class TestPipelineChroma:
    def test_returns_dict(self, chord_audio):
        y, sr = chord_audio
        result = pipeline_chroma(y, sr)
        assert isinstance(result, dict)

    def test_required_keys_present(self, chord_audio):
        y, sr = chord_audio
        result = pipeline_chroma(y, sr)
        for key in ("cqt", "cens", "cqt_raw", "y_harmonic", "tuning"):
            assert key in result, f"Missing key: {key}"

    def test_cqt_is_12_row_array(self, chord_audio):
        y, sr = chord_audio
        result = pipeline_chroma(y, sr)
        assert result["cqt"].shape[0] == 12

    def test_cens_is_12_row_array(self, chord_audio):
        y, sr = chord_audio
        result = pipeline_chroma(y, sr)
        assert result["cens"].shape[0] == 12

    def test_y_harmonic_same_length_as_input(self, chord_audio):
        y, sr = chord_audio
        result = pipeline_chroma(y, sr)
        assert result["y_harmonic"].shape == y.shape

    def test_tuning_is_float(self, chord_audio):
        y, sr = chord_audio
        result = pipeline_chroma(y, sr)
        assert isinstance(result["tuning"], float)

    def test_all_arrays_finite(self, chord_audio):
        y, sr = chord_audio
        result = pipeline_chroma(y, sr)
        for key in ("cqt", "cens", "cqt_raw", "y_harmonic"):
            assert np.all(np.isfinite(result[key])), f"{key} contains non-finite values"
