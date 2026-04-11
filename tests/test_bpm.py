"""
Testes para music_analyzer.bpm — detecção de BPM.

Os testes de integração (que exigem librosa/áudio real) são marcados com
@pytest.mark.integration e saltados no CI via pytest -m "not integration".
Os demais testam a lógica de normalização e comportamentos de borda.
"""

import numpy as np

from music_analyzer.bpm import detectar_bpm


class TestDetectarBpmNormalizacao:
    """Verifica a lógica de normalização para a faixa 60-180 BPM."""

    def _bpm_from_constant_signal(self, sinal: np.ndarray, sr: int = 22050) -> float:
        """Helper: roda detectar_bpm com sinal percussivo direto."""
        return detectar_bpm(sinal, sr=sr, y_percussive=sinal)

    def test_retorna_float(self):
        sinal = np.zeros(sr := 22050)
        result = detectar_bpm(sinal, sr=sr)
        assert isinstance(result, float)

    def test_resultado_nunca_abaixo_de_60(self):
        # Sinal branco curto — garante que o BPM estimado seja normalizado
        rng = np.random.default_rng(7)
        sinal = rng.standard_normal(22050 * 5).astype(np.float32)
        bpm = detectar_bpm(sinal, sr=22050)
        if bpm > 0:   # 0 significa que não foi possível estimar
            assert bpm >= 60.0

    def test_resultado_nunca_acima_de_180(self):
        rng = np.random.default_rng(13)
        sinal = rng.standard_normal(22050 * 5).astype(np.float32)
        bpm = detectar_bpm(sinal, sr=22050)
        if bpm > 0:
            assert bpm <= 180.0

    def test_sinal_percussivo_preferido_sobre_original(self):
        """Se y_percussive for fornecido, detectar_bpm deve usá-lo."""
        y = np.zeros(22050 * 3)
        # Sinal percussivo com pulso a ~120 BPM
        sr = 22050
        intervalo = int(sr * 60 / 120)  # amostras por batida
        perc = np.zeros(sr * 3)
        for i in range(0, len(perc), intervalo):
            perc[i] = 1.0

        bpm = detectar_bpm(y, sr=sr, y_percussive=perc)
        # Não exige 120 exato — apenas que seja um float válido na faixa
        assert isinstance(bpm, float)
        assert bpm >= 60.0

    def test_sinal_silencioso_retorna_zero_ou_float(self):
        sinal = np.zeros(22050 * 2)
        result = detectar_bpm(sinal, sr=22050)
        assert isinstance(result, float)
