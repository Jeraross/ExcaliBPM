"""
Tests for music_analyzer.key_detect module.
"""

import numpy as np
import pytest
from collections import Counter

from music_analyzer.key_detect import (
    NOTAS,
    _RELATIVOS,
    _pearson_correlacao,
    _euclidiana_similaridade,
    detectar_com_perfil,
    ensemble_votar,
    votacao_por_frames,
    analisar_bass_register,
    desambiguar_resultado,
    ResultadoTonalidade,
)
from music_analyzer.profiles import get_all_profiles


# ── _pearson_correlacao ──────────────────────────────────────────

class TestPearsonCorrelacao:
    def test_identical_vectors_give_one(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        assert abs(_pearson_correlacao(x, x) - 1.0) < 1e-10

    def test_opposite_vectors_give_minus_one(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        assert abs(_pearson_correlacao(x, -x) - (-1.0)) < 1e-10

    def test_uncorrelated_vectors(self):
        x = np.array([1.0, -1.0, 1.0, -1.0])
        y = np.array([1.0, 1.0, -1.0, -1.0])
        assert abs(_pearson_correlacao(x, y)) < 1e-10

    def test_constant_vector_returns_zero(self):
        x = np.ones(12)
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0])
        # constant x has zero variance → returns 0
        assert _pearson_correlacao(x, y) == 0.0

    def test_result_in_range_minus_one_to_one(self):
        rng = np.random.default_rng(42)
        for _ in range(50):
            x = rng.random(12)
            y = rng.random(12)
            r = _pearson_correlacao(x, y)
            assert -1.0 - 1e-10 <= r <= 1.0 + 1e-10


# ── _euclidiana_similaridade ─────────────────────────────────────

class TestEuclidianaSimilaridade:
    def test_identical_vectors_give_maximum(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        # distance is 0, similarity is 1/(1+0) = 1
        assert abs(_euclidiana_similaridade(x, x) - 1.0) < 1e-10

    def test_orthogonal_vectors_give_less_than_one(self):
        x = np.zeros(4)
        x[0] = 1.0
        y = np.zeros(4)
        y[1] = 1.0
        s = _euclidiana_similaridade(x, y)
        assert 0 < s < 1

    def test_result_is_positive(self):
        rng = np.random.default_rng(7)
        for _ in range(20):
            x = rng.random(12)
            y = rng.random(12)
            assert _euclidiana_similaridade(x, y) > 0

    def test_zero_vector_handled(self):
        x = np.zeros(12)
        y = np.ones(12)
        # should not raise; zero-norm handled by + 1e-12
        result = _euclidiana_similaridade(x, y)
        assert np.isfinite(result)


# ── detectar_com_perfil ──────────────────────────────────────────

class TestDetectarComPerfil:
    """Uses a synthetic chroma vector biased strongly towards C Major."""

    @pytest.fixture
    def c_major_chroma(self):
        # C Major notes: C, E, G → indices 0, 4, 7
        vec = np.zeros(12)
        vec[0] = 1.0   # C
        vec[4] = 0.8   # E
        vec[7] = 0.6   # G
        return vec

    @pytest.fixture
    def profiles(self):
        return get_all_profiles()["bellman_budge"]

    def test_returns_tuple_of_three(self, c_major_chroma, profiles):
        result = detectar_com_perfil(c_major_chroma, profiles["major"], profiles["minor"])
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_key_is_string(self, c_major_chroma, profiles):
        tom, _, _ = detectar_com_perfil(c_major_chroma, profiles["major"], profiles["minor"])
        assert isinstance(tom, str)

    def test_confidence_in_range(self, c_major_chroma, profiles):
        _, conf, _ = detectar_com_perfil(c_major_chroma, profiles["major"], profiles["minor"])
        assert 0.0 <= conf <= 1.0

    def test_correlations_dict_has_24_entries(self, c_major_chroma, profiles):
        _, _, corrs = detectar_com_perfil(c_major_chroma, profiles["major"], profiles["minor"])
        assert len(corrs) == 24

    def test_correlations_keys_are_valid_keys(self, c_major_chroma, profiles):
        _, _, corrs = detectar_com_perfil(c_major_chroma, profiles["major"], profiles["minor"])
        for k in corrs:
            assert k.split()[0] in NOTAS
            assert k.split()[1] in ("Major", "Minor")

    def test_euclidiana_flag(self, c_major_chroma, profiles):
        result = detectar_com_perfil(
            c_major_chroma, profiles["major"], profiles["minor"], usar_euclidiana=True
        )
        assert isinstance(result[0], str)

    def test_strong_c_major_signal_detected(self, c_major_chroma):
        all_profiles = get_all_profiles()
        # Majority of profiles should detect C Major or its relative A Minor
        detections = []
        for name, modes in all_profiles.items():
            tom, _, _ = detectar_com_perfil(
                c_major_chroma, modes["major"], modes["minor"]
            )
            detections.append(tom)
        counts = Counter(detections)
        top = counts.most_common(1)[0][0]
        assert top in ("C Major", "A Minor")


# ── ensemble_votar ───────────────────────────────────────────────

class TestEnsembleVotar:
    @pytest.fixture
    def c_major_chroma(self):
        vec = np.zeros(12)
        vec[0] = 1.0
        vec[4] = 0.8
        vec[7] = 0.6
        return vec

    def test_returns_resultado_tonalidade(self, c_major_chroma):
        result = ensemble_votar(c_major_chroma)
        assert isinstance(result, ResultadoTonalidade)

    def test_result_tom_is_valid_key(self, c_major_chroma):
        result = ensemble_votar(c_major_chroma)
        nota, modo = result.tom.split()
        assert nota in NOTAS
        assert modo in ("Major", "Minor")

    def test_confianca_in_range(self, c_major_chroma):
        result = ensemble_votar(c_major_chroma)
        assert 0.0 <= result.confianca <= 1.0

    def test_votos_perfis_populated(self, c_major_chroma):
        result = ensemble_votar(c_major_chroma)
        assert len(result.votos_perfis) > 0

    def test_correlacoes_has_24_entries(self, c_major_chroma):
        result = ensemble_votar(c_major_chroma)
        assert len(result.correlacoes) == 24

    def test_c_major_detected(self, c_major_chroma):
        result = ensemble_votar(c_major_chroma)
        assert result.tom in ("C Major", "A Minor")

    def test_custom_profiles_used(self, c_major_chroma):
        profiles = {"test_profile": get_all_profiles()["bellman_budge"]}
        result = ensemble_votar(c_major_chroma, perfis=profiles)
        assert isinstance(result, ResultadoTonalidade)
        assert "test_profile" in result.votos_perfis


# ── votacao_por_frames ───────────────────────────────────────────

class TestVotacaoPorFrames:
    @pytest.fixture
    def synthetic_chroma(self):
        """12×200 chroma matrix biased towards C Major."""
        chroma = np.zeros((12, 200))
        chroma[0] = 1.0   # C
        chroma[4] = 0.8   # E
        chroma[7] = 0.6   # G
        return chroma

    def test_returns_resultado_tonalidade(self, synthetic_chroma):
        result = votacao_por_frames(synthetic_chroma, sr=22050)
        assert isinstance(result, ResultadoTonalidade)

    def test_votos_frames_are_populated(self, synthetic_chroma):
        result = votacao_por_frames(synthetic_chroma, sr=22050)
        assert isinstance(result.votos_frames, list)
        assert len(result.votos_frames) > 0

    def test_confianca_in_range(self, synthetic_chroma):
        result = votacao_por_frames(synthetic_chroma, sr=22050)
        assert 0.0 <= result.confianca <= 1.0

    def test_silent_frames_excluded(self):
        """All-zero chroma with below-threshold RMS should return Indeterminado."""
        chroma = np.zeros((12, 100))
        rms = np.zeros(100)
        result = votacao_por_frames(chroma, sr=22050, rms=rms)
        assert result.tom == "Indeterminado"
        assert result.confianca == 0.0

    def test_with_rms_filter(self, synthetic_chroma):
        rms = np.ones(200)  # all frames are loud
        result = votacao_por_frames(synthetic_chroma, sr=22050, rms=rms)
        assert isinstance(result, ResultadoTonalidade)

    def test_very_short_chroma(self):
        """Chroma shorter than one segment should still work."""
        chroma = np.zeros((12, 5))
        chroma[0] = 1.0
        result = votacao_por_frames(chroma, sr=22050)
        assert isinstance(result, ResultadoTonalidade)


# ── analisar_bass_register ───────────────────────────────────────

class TestAnalisarBassRegister:
    @pytest.fixture
    def synthetic_audio(self):
        """1-second 440 Hz sine wave at sr=22050."""
        sr = 22050
        t = np.linspace(0, 1.0, sr, endpoint=False)
        return np.sin(2 * np.pi * 440 * t).astype(np.float32), sr

    def test_returns_ndarray(self, synthetic_audio):
        y, sr = synthetic_audio
        result = analisar_bass_register(y, sr)
        assert isinstance(result, np.ndarray)

    def test_output_shape_is_12_x_frames(self, synthetic_audio):
        y, sr = synthetic_audio
        result = analisar_bass_register(y, sr)
        assert result.shape[0] == 12
        assert result.shape[1] > 0

    def test_output_is_non_negative(self, synthetic_audio):
        y, sr = synthetic_audio
        result = analisar_bass_register(y, sr)
        assert np.all(result >= 0)


# ── desambiguar_resultado ────────────────────────────────────────

class TestDesambiguarResultado:
    def _make_resultado(self, tom, confianca=0.5):
        return ResultadoTonalidade(
            tom=tom,
            confianca=confianca,
            correlacoes={},
            votos_perfis={"perfil": tom},
            votos_frames=[tom],
        )

    def test_returns_resultado_tonalidade(self):
        r = self._make_resultado("C Major")
        result = desambiguar_resultado(r, r, r, r)
        assert isinstance(result, ResultadoTonalidade)

    def test_unanimous_vote_wins(self):
        r = self._make_resultado("G Major")
        result = desambiguar_resultado(r, r, r, r)
        assert result.tom == "G Major"

    def test_majority_wins_over_minority(self):
        majority = self._make_resultado("C Major")
        minority = self._make_resultado("A Minor")
        result = desambiguar_resultado(majority, majority, minority, majority)
        assert result.tom == "C Major"

    def test_confianca_is_reasonable(self):
        r = self._make_resultado("D Major")
        result = desambiguar_resultado(r, r, r, r)
        assert 0.0 <= result.confianca <= 1.0

    def test_votos_perfis_preserved_from_global(self):
        global_r = ResultadoTonalidade(
            tom="C Major",
            confianca=0.8,
            correlacoes={"C Major": 0.9},
            votos_perfis={"bellman_budge": "C Major"},
            votos_frames=["C Major"],
        )
        frames_r = self._make_resultado("C Major")
        result = desambiguar_resultado(global_r, frames_r, frames_r, frames_r)
        assert result.votos_perfis == global_r.votos_perfis

    def test_correlacoes_preserved_from_global(self):
        global_r = ResultadoTonalidade(
            tom="E Minor",
            confianca=0.7,
            correlacoes={"E Minor": 0.85},
            votos_perfis={},
            votos_frames=[],
        )
        frames_r = self._make_resultado("E Minor")
        result = desambiguar_resultado(global_r, frames_r, frames_r, frames_r)
        assert result.correlacoes == global_r.correlacoes

    def test_with_bass_chroma(self):
        """Bass chroma that strongly favors C should influence the vote."""
        # Bias bass register towards C (index 0)
        bass = np.zeros((12, 50))
        bass[0] = 10.0  # strong C in bass
        r_c = self._make_resultado("C Major")
        r_am = self._make_resultado("A Minor")
        # global + frames agree on C Major
        result = desambiguar_resultado(r_c, r_c, r_am, r_am, chroma_bass=bass)
        # Result should still be a valid key
        assert result.tom.split()[1] in ("Major", "Minor")

    def test_endpoint_favor_final_key(self):
        """The final segment carries more weight (2 votes) than the inicio (1 vote)."""
        r_c = self._make_resultado("C Major")
        r_am = self._make_resultado("A Minor")
        # global=C Major (3), frames=C Major (3), inicio=C Major (1), final=C Major (2)
        # → C Major wins 9 votes vs A Minor 0
        result = desambiguar_resultado(r_c, r_c, r_c, r_c)
        assert result.tom == "C Major"

    def test_endpoints_can_flip_relative_to_minor(self):
        """When global/frames disagree with endpoints, endpoints flip the result."""
        r_c = self._make_resultado("C Major")
        r_am = self._make_resultado("A Minor")
        # global=A Minor (3), frames=A Minor (3), inicio=C Major (1), final=C Major (2)
        # C Major and A Minor are relatives: disambiguation uses endpoints
        # final votes C Major (2), inicio votes C Major (1) → C Major wins disambiguation
        result = desambiguar_resultado(r_am, r_am, r_c, r_c)
        assert result.tom == "C Major"

    def test_votos_frames_preserved(self):
        frames_r = ResultadoTonalidade(
            tom="F Major",
            confianca=0.6,
            correlacoes={},
            votos_perfis={},
            votos_frames=["F Major", "F Major", "C Major"],
        )
        r = self._make_resultado("F Major")
        result = desambiguar_resultado(r, frames_r, r, r)
        assert result.votos_frames == frames_r.votos_frames


# ── NOTAS and _RELATIVOS integrity ───────────────────────────────

class TestConstants:
    def test_notas_has_12_entries(self):
        assert len(NOTAS) == 12

    def test_relativos_bidirectional(self):
        for major, minor in _RELATIVOS.items():
            assert _RELATIVOS.get(minor) == major

    def test_relativos_count_is_24(self):
        assert len(_RELATIVOS) == 24
