"""
Shared fixtures across all tests.
"""

import numpy as np
import pytest

from music_analyzer.models import MusicAnalysis


# ── Synthetic chroma vectors ─────────────────────────────────────────────────

@pytest.fixture
def chroma_c_major() -> np.ndarray:
    """
    Chroma with strong C Major presence (C-E-G with high intensity,
    notes outside the C Major scale near zero).
    """
    # C  C# D  D# E  F  F# G  G# A  A# B
    v = np.array([5.0, 0.1, 1.5, 0.1, 3.5, 1.0, 0.1, 4.0, 0.1, 1.0, 0.1, 0.5])
    return v / v.sum()


@pytest.fixture
def chroma_a_minor() -> np.ndarray:
    """
    Chroma with strong A Minor presence (A-C-E with high intensity).
    """
    # C  C# D  D# E  F  F# G  G# A  A# B
    v = np.array([3.0, 0.1, 1.0, 0.1, 3.0, 1.0, 0.1, 1.5, 0.1, 5.0, 0.1, 0.5])
    return v / v.sum()


@pytest.fixture
def chroma_g_major() -> np.ndarray:
    """Chroma with strong G Major presence (G-B-D)."""
    # C  C# D  D# E  F  F# G  G# A  A# B
    v = np.array([1.0, 0.1, 2.0, 0.1, 1.5, 0.1, 1.5, 5.0, 0.1, 1.0, 0.1, 3.5])
    return v / v.sum()


@pytest.fixture
def chroma_matrix_c_major(chroma_c_major) -> np.ndarray:
    """
    Chroma matrix (12 x N_frames) with a repeated C Major signal,
    long enough for frame voting (~4.6 s at hop=512, sr=22050).
    """
    return np.tile(chroma_c_major[:, None], (1, 200))


# ── Example MusicAnalysis ────────────────────────────────────────────────────

@pytest.fixture
def sample_analysis() -> MusicAnalysis:
    return MusicAnalysis(
        key="C Major",
        key_confidence=0.85,
        key_start="C Major",
        start_confidence=0.80,
        key_end="G Major",
        end_confidence=0.75,
        bpm=128.0,
        duration_seconds=212.5,
        file="track.wav",
    )
