"""
BPM detection optimized for DJ mixing.

Uses the isolated percussive signal for a cleaner onset envelope,
with normalization to the 60-180 BPM range used in DJ sets.
"""

import numpy as np
import librosa


def detect_bpm(
    y: np.ndarray,
    sr: int,
    y_percussive: np.ndarray | None = None,
) -> float:
    """
    Detect BPM from an audio signal.

    If y_percussive is provided, it is used for the onset envelope
    (more accurate by ignoring harmonic content).
    """
    signal = y_percussive if y_percussive is not None else y
    onset_env = librosa.onset.onset_strength(y=signal, sr=sr)

    # prior=None lets librosa estimate without bias
    bpm_array = librosa.feature.tempo(
        onset_envelope=onset_env,
        sr=sr,
        aggregate=None,  # returns multiple estimates over time
    )

    if len(bpm_array) == 0:
        return 0.0

    # Take the most frequent estimate (mode)
    # When aggregate=None, an array of estimates over time is returned
    if bpm_array.ndim > 0 and len(bpm_array) > 1:
        rounded_bpm = np.round(bpm_array).astype(int)
        values, counts = np.unique(rounded_bpm, return_counts=True)
        bpm = float(values[np.argmax(counts)])
    else:
        bpm = float(bpm_array[0]) if hasattr(bpm_array, "__len__") else float(bpm_array)

    # Normalize to the useful DJ range (60-180 BPM)
    while bpm < 60:
        bpm *= 2
    while bpm > 180:
        bpm /= 2

    return round(bpm, 1)
