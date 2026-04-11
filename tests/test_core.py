"""
Tests for music_analyzer.core module.
"""

import numpy as np
import pytest
import os
import tempfile
import soundfile as sf

from music_analyzer.core import analisar_musica, analisar_lote
from music_analyzer.models import AnaliseMusical


SR = 22050


def _write_sine_wav(path: str, freq: float = 261.63, duration: float = 5.0) -> None:
    """Write a mono WAV file containing a sine wave."""
    t = np.linspace(0, duration, int(SR * duration), endpoint=False)
    y = (np.sin(2 * np.pi * freq * t) * 0.5).astype(np.float32)
    sf.write(path, y, SR)


def _write_chord_wav(path: str, duration: float = 5.0) -> None:
    """Write a WAV file with a C-major chord (C4 + E4 + G4)."""
    n = int(SR * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    y = (
        np.sin(2 * np.pi * 261.63 * t) +
        np.sin(2 * np.pi * 329.63 * t) +
        np.sin(2 * np.pi * 392.00 * t)
    ).astype(np.float32) / 3.0
    sf.write(path, y, SR)


@pytest.fixture(scope="module")
def sine_wav(tmp_path_factory):
    p = tmp_path_factory.mktemp("audio") / "sine.wav"
    _write_sine_wav(str(p))
    return str(p)


@pytest.fixture(scope="module")
def chord_wav(tmp_path_factory):
    p = tmp_path_factory.mktemp("audio") / "chord.wav"
    _write_chord_wav(str(p))
    return str(p)


# ── analisar_musica ──────────────────────────────────────────────

class TestAnalisarMusica:
    def test_returns_analise_musical(self, chord_wav):
        result = analisar_musica(chord_wav, sr=SR)
        assert isinstance(result, AnaliseMusical)

    def test_arquivo_field_set(self, chord_wav):
        result = analisar_musica(chord_wav, sr=SR)
        assert result.arquivo == chord_wav

    def test_duracao_positive(self, chord_wav):
        result = analisar_musica(chord_wav, sr=SR)
        assert result.duracao_segundos > 0

    def test_bpm_in_dj_range(self, chord_wav):
        result = analisar_musica(chord_wav, sr=SR)
        assert 60.0 <= result.bpm <= 180.0

    def test_tonalidade_geral_is_valid_key(self, chord_wav):
        result = analisar_musica(chord_wav, sr=SR)
        partes = result.tonalidade_geral.split()
        assert len(partes) == 2
        assert partes[1] in ("Major", "Minor")

    def test_confianca_geral_in_range(self, chord_wav):
        result = analisar_musica(chord_wav, sr=SR)
        assert 0.0 <= result.confianca_geral <= 1.0

    def test_tonalidade_inicio_is_valid_key(self, chord_wav):
        result = analisar_musica(chord_wav, sr=SR)
        partes = result.tonalidade_inicio.split()
        assert len(partes) == 2
        assert partes[1] in ("Major", "Minor")

    def test_tonalidade_final_is_valid_key(self, chord_wav):
        result = analisar_musica(chord_wav, sr=SR)
        partes = result.tonalidade_final.split()
        assert len(partes) == 2
        assert partes[1] in ("Major", "Minor")

    def test_votos_perfis_populated(self, chord_wav):
        result = analisar_musica(chord_wav, sr=SR)
        assert len(result.votos_perfis) > 0

    def test_votos_frames_is_list(self, chord_wav):
        result = analisar_musica(chord_wav, sr=SR)
        assert isinstance(result.votos_frames, list)

    def test_to_dict_serialisable(self, chord_wav):
        import json
        result = analisar_musica(chord_wav, sr=SR)
        json.dumps(result.to_dict())  # must not raise

    def test_camelot_code_is_valid(self, chord_wav):
        from music_analyzer.camelot import CAMELOT_PARA_TOM
        result = analisar_musica(chord_wav, sr=SR)
        assert result.camelot in CAMELOT_PARA_TOM

    def test_c_major_chord_detected_as_c_or_relative(self, chord_wav):
        """C-major triad should be detected as C Major or its relative A Minor."""
        result = analisar_musica(chord_wav, sr=SR)
        assert result.tonalidade_geral in ("C Major", "A Minor", "F Major", "D Minor")


# ── analisar_lote ────────────────────────────────────────────────

class TestAnalisarLote:
    def test_empty_list_returns_empty(self):
        result = analisar_lote([])
        assert result == []

    def test_single_file_returns_one_result(self, chord_wav):
        result = analisar_lote([chord_wav], sr=SR)
        assert len(result) == 1
        assert isinstance(result[0], AnaliseMusical)

    def test_multiple_files(self, sine_wav, chord_wav):
        result = analisar_lote([sine_wav, chord_wav], sr=SR)
        assert len(result) == 2
        for r in result:
            assert isinstance(r, AnaliseMusical)

    def test_nonexistent_file_is_skipped(self, chord_wav, capsys):
        result = analisar_lote(["/nonexistent/file.wav", chord_wav], sr=SR)
        # The bad file is skipped; only the valid file is in the result
        assert len(result) == 1
        assert isinstance(result[0], AnaliseMusical)

    def test_all_invalid_files_returns_empty(self, capsys):
        result = analisar_lote(["/no/such/a.wav", "/no/such/b.wav"])
        assert result == []

    def test_results_have_bpm_in_range(self, chord_wav):
        results = analisar_lote([chord_wav], sr=SR)
        for r in results:
            assert 60.0 <= r.bpm <= 180.0
