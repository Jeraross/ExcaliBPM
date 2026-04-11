"""
Testes para music_analyzer.key_detect — detecção de tonalidade.
"""

import numpy as np

from music_analyzer.key_detect import (
    ResultadoTonalidade,
    _euclidiana_similaridade,
    _pearson_correlacao,
    desambiguar_resultado,
    detectar_com_perfil,
    ensemble_votar,
    votacao_por_frames,
)
from music_analyzer.profiles import get_all_profiles


# ── _pearson_correlacao ──────────────────────────────────────────────────────

class TestPearsonCorrelacao:
    def test_correlacao_perfeita(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        assert abs(_pearson_correlacao(x, x) - 1.0) < 1e-9

    def test_correlacao_perfeita_negativa(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        y = -x
        assert abs(_pearson_correlacao(x, y) + 1.0) < 1e-9

    def test_vetor_zero_retorna_zero(self):
        x = np.zeros(12)
        y = np.array([1.0] * 12)
        assert _pearson_correlacao(x, y) == 0.0

    def test_resultado_entre_menos1_e_1(self):
        rng = np.random.default_rng(42)
        for _ in range(20):
            x = rng.random(12)
            y = rng.random(12)
            r = _pearson_correlacao(x, y)
            assert -1.0 - 1e-9 <= r <= 1.0 + 1e-9


# ── _euclidiana_similaridade ─────────────────────────────────────────────────

class TestEuclidianaSimialaridade:
    def test_vetor_identico_retorna_1(self):
        x = np.array([1.0, 0.5, 0.3, 0.8, 0.2, 0.1, 0.0, 0.9, 0.4, 0.6, 0.1, 0.3])
        assert abs(_euclidiana_similaridade(x, x) - 1.0) < 1e-9

    def test_resultado_positivo(self):
        rng = np.random.default_rng(0)
        x, y = rng.random(12), rng.random(12)
        assert _euclidiana_similaridade(x, y) > 0

    def test_resultado_no_maximo_1(self):
        rng = np.random.default_rng(1)
        x, y = rng.random(12), rng.random(12)
        assert _euclidiana_similaridade(x, y) <= 1.0 + 1e-9

    def test_vetor_zero_nao_explode(self):
        x = np.zeros(12)
        y = np.ones(12)
        result = _euclidiana_similaridade(x, y)
        assert np.isfinite(result)


# ── detectar_com_perfil ──────────────────────────────────────────────────────

class TestDetectarComPerfil:
    def test_retorna_tripla(self, chroma_c_major):
        perfis = get_all_profiles()
        p = perfis["bellman_budge"]
        result = detectar_com_perfil(chroma_c_major, p["major"], p["minor"])
        assert len(result) == 3

    def test_tonalidade_retornada_e_string_valida(self, chroma_c_major):
        perfis = get_all_profiles()
        p = perfis["bellman_budge"]
        tom, confianca, corrs = detectar_com_perfil(chroma_c_major, p["major"], p["minor"])
        assert isinstance(tom, str)
        assert "Major" in tom or "Minor" in tom

    def test_confianca_entre_0_e_1(self, chroma_c_major):
        perfis = get_all_profiles()
        p = perfis["bellman_budge"]
        _, confianca, _ = detectar_com_perfil(chroma_c_major, p["major"], p["minor"])
        assert 0.0 <= confianca <= 1.0

    def test_correlacoes_tem_24_entradas(self, chroma_c_major):
        perfis = get_all_profiles()
        p = perfis["bellman_budge"]
        _, _, corrs = detectar_com_perfil(chroma_c_major, p["major"], p["minor"])
        assert len(corrs) == 24

    def test_chroma_c_major_detecta_c_major(self, chroma_c_major):
        perfis = get_all_profiles()
        p = perfis["bellman_budge"]
        tom, _, _ = detectar_com_perfil(chroma_c_major, p["major"], p["minor"])
        assert tom == "C Major"

    def test_modo_euclidiano_nao_explode(self, chroma_c_major):
        perfis = get_all_profiles()
        p = perfis["albrecht_shanahan"]
        tom, confianca, corrs = detectar_com_perfil(
            chroma_c_major, p["major"], p["minor"], usar_euclidiana=True
        )
        assert isinstance(tom, str)
        assert 0.0 <= confianca <= 1.0


# ── ensemble_votar ───────────────────────────────────────────────────────────

class TestEnsembleVotar:
    def test_retorna_resultado_tonalidade(self, chroma_c_major):
        r = ensemble_votar(chroma_c_major)
        assert isinstance(r, ResultadoTonalidade)

    def test_confianca_entre_0_e_1(self, chroma_c_major):
        r = ensemble_votar(chroma_c_major)
        assert 0.0 <= r.confianca <= 1.0

    def test_votos_por_perfil_preenchidos(self, chroma_c_major):
        r = ensemble_votar(chroma_c_major)
        assert len(r.votos_perfis) > 0

    def test_chroma_c_major_vence_com_c_major(self, chroma_c_major):
        r = ensemble_votar(chroma_c_major)
        assert r.tom == "C Major"

    def test_chroma_g_major_detecta_g_major(self, chroma_g_major):
        r = ensemble_votar(chroma_g_major)
        assert r.tom == "G Major"

    def test_perfis_customizados_sao_usados(self, chroma_c_major):
        # Passa apenas um perfil; votos_perfis deve ter exatamente 1 entrada
        perfis = {"bellman_budge": get_all_profiles()["bellman_budge"]}
        r = ensemble_votar(chroma_c_major, perfis=perfis)
        assert len(r.votos_perfis) == 1


# ── votacao_por_frames ───────────────────────────────────────────────────────

class TestVotacaoPorFrames:
    def test_retorna_resultado_tonalidade(self, chroma_matrix_c_major):
        r = votacao_por_frames(chroma_matrix_c_major, sr=22050, hop_length=512)
        assert isinstance(r, ResultadoTonalidade)

    def test_votos_frames_preenchidos(self, chroma_matrix_c_major):
        r = votacao_por_frames(chroma_matrix_c_major, sr=22050, hop_length=512)
        assert r.votos_frames is not None
        assert len(r.votos_frames) > 0

    def test_chroma_c_major_detecta_c_major(self, chroma_matrix_c_major):
        r = votacao_por_frames(chroma_matrix_c_major, sr=22050, hop_length=512)
        assert r.tom == "C Major"

    def test_confianca_entre_0_e_1(self, chroma_matrix_c_major):
        r = votacao_por_frames(chroma_matrix_c_major, sr=22050, hop_length=512)
        assert 0.0 <= r.confianca <= 1.0

    def test_matriz_zerada_retorna_indeterminado(self):
        chroma_zero = np.zeros((12, 50))
        r = votacao_por_frames(chroma_zero, sr=22050, hop_length=512)
        assert r.tom == "Indeterminado"
        assert r.confianca == 0.0

    def test_filtro_de_silencio_funciona(self, chroma_matrix_c_major):
        # RMS zerado deve filtrar todos os frames → Indeterminado
        rms_zero = np.zeros(chroma_matrix_c_major.shape[1])
        r = votacao_por_frames(
            chroma_matrix_c_major, sr=22050, hop_length=512, rms=rms_zero
        )
        assert r.tom == "Indeterminado"


# ── desambiguar_resultado ────────────────────────────────────────────────────

class TestDesambiguarResultado:
    def _make_resultado(self, tom: str, confianca: float = 0.8) -> ResultadoTonalidade:
        return ResultadoTonalidade(
            tom=tom, confianca=confianca, correlacoes={}, votos_perfis={}
        )

    def test_retorna_resultado_tonalidade(self):
        r_global = self._make_resultado("C Major")
        r_frames = self._make_resultado("C Major")
        r_inicio = self._make_resultado("C Major")
        r_final = self._make_resultado("C Major")
        resultado = desambiguar_resultado(r_global, r_frames, r_inicio, r_final)
        assert isinstance(resultado, ResultadoTonalidade)

    def test_consenso_absoluto_retorna_tom_correto(self):
        r = self._make_resultado("G Major")
        resultado = desambiguar_resultado(r, r, r, r)
        assert resultado.tom == "G Major"

    def test_confianca_entre_0_e_1(self):
        r = self._make_resultado("D Minor")
        resultado = desambiguar_resultado(r, r, r, r)
        assert 0.0 <= resultado.confianca <= 1.0

    def test_sem_bass_nao_explode(self):
        r = self._make_resultado("A Minor")
        resultado = desambiguar_resultado(r, r, r, r, chroma_bass=None)
        assert resultado.tom == "A Minor"

    def test_desambiguacao_com_bass(self):
        # Conflito: global e frames votam em C Major, final vota em A Minor
        r_global = self._make_resultado("C Major")
        r_frames = self._make_resultado("C Major")
        r_inicio = self._make_resultado("C Major")
        r_final = self._make_resultado("A Minor")

        # Bass forte em C (índice 0)
        chroma_bass = np.zeros((12, 10))
        chroma_bass[0] = 5.0   # C muito forte no baixo

        resultado = desambiguar_resultado(r_global, r_frames, r_inicio, r_final, chroma_bass)
        # C Major tem mais votos pesados (3+3+1=7 vs 2)
        assert resultado.tom == "C Major"
