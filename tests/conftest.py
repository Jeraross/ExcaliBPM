"""
Fixtures compartilhadas entre os testes.
"""

import numpy as np
import pytest

from music_analyzer.models import AnaliseMusical


# ── Vetores de chroma sintéticos ────────────────────────────────────────────

@pytest.fixture
def chroma_c_major() -> np.ndarray:
    """
    Chroma com forte presença de C Major (C-E-G com intensidades altas,
    notas fora da escala de C Major próximas de zero).
    """
    # C  C# D  D# E  F  F# G  G# A  A# B
    v = np.array([5.0, 0.1, 1.5, 0.1, 3.5, 1.0, 0.1, 4.0, 0.1, 1.0, 0.1, 0.5])
    return v / v.sum()


@pytest.fixture
def chroma_a_minor() -> np.ndarray:
    """
    Chroma com forte presença de A Minor (A-C-E com intensidades altas).
    """
    # C  C# D  D# E  F  F# G  G# A  A# B
    v = np.array([3.0, 0.1, 1.0, 0.1, 3.0, 1.0, 0.1, 1.5, 0.1, 5.0, 0.1, 0.5])
    return v / v.sum()


@pytest.fixture
def chroma_g_major() -> np.ndarray:
    """Chroma com forte presença de G Major (G-B-D)."""
    # C  C# D  D# E  F  F# G  G# A  A# B
    v = np.array([1.0, 0.1, 2.0, 0.1, 1.5, 0.1, 1.5, 5.0, 0.1, 1.0, 0.1, 3.5])
    return v / v.sum()


@pytest.fixture
def chroma_matrix_c_major(chroma_c_major) -> np.ndarray:
    """
    Matriz de chroma (12 x N_frames) com sinal C Major repetido,
    suficientemente longa para votação por frames.
    """
    # 200 frames ≈ ~4.6 s com hop=512 e sr=22050
    return np.tile(chroma_c_major[:, None], (1, 200))


# ── AnaliseMusical de exemplo ────────────────────────────────────────────────

@pytest.fixture
def analise_exemplo() -> AnaliseMusical:
    return AnaliseMusical(
        tonalidade_geral="C Major",
        confianca_geral=0.85,
        tonalidade_inicio="C Major",
        confianca_inicio=0.80,
        tonalidade_final="G Major",
        confianca_final=0.75,
        bpm=128.0,
        duracao_segundos=212.5,
        arquivo="track.wav",
    )
