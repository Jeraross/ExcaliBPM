"""
Optimized chroma extraction pipeline for key detection.

Implements best practices from the literature:
- Aggressive harmonic separation (HPSS margin=8)
- CQT with 36 bins/octave (3 per semitone)
- Automatic tuning correction
- Non-local filtering + temporal median
- Energy weighting (RMS)
"""

import numpy as np
import scipy.ndimage
import librosa


def extract_harmonic(y: np.ndarray, margin: int = 8) -> np.ndarray:
    """
    Isolate the harmonic content of the audio via HPSS.

    margin=8 is aggressive — suppresses nearly all percussion and noise
    while preserving melody, chords, and bass lines. Ideal for key
    detection where percussion pollutes the chroma.
    """
    return librosa.effects.harmonic(y=y, margin=margin)


def estimate_tuning(y: np.ndarray, sr: int) -> float:
    """
    Estimate the tuning deviation of the audio relative to A440.

    Many recordings are slightly out of tune (±10-50 cents).
    Without correction, chroma energy leaks into adjacent bins,
    reducing key detection accuracy.
    """
    return librosa.estimate_tuning(y=y, sr=sr, n_fft=8192)


def extract_chroma_cqt(
    y: np.ndarray,
    sr: int,
    hop_length: int = 512,
    tuning: float | None = None,
) -> np.ndarray:
    """
    Extract chroma via Constant-Q Transform with optimized parameters.

    bins_per_octave=36 (3 bins/semitone) significantly improves
    resolution at low frequencies, reducing energy leakage between
    nearby notes — especially between tonic and dominant.
    """
    if tuning is None:
        tuning = estimate_tuning(y, sr)

    chroma = librosa.feature.chroma_cqt(
        y=y,
        sr=sr,
        hop_length=hop_length,
        fmin=librosa.note_to_hz("C1"),
        n_chroma=12,
        n_octaves=7,
        bins_per_octave=36,
        norm=np.inf,
        tuning=tuning,
    )
    return chroma


def extract_chroma_cens(
    y: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> np.ndarray:
    """
    Extract CENS chroma — more robust to timbre variations and
    recording quality, but less precise for distinguishing tonic
    from dominant. Used as a secondary voter in the ensemble.
    """
    return librosa.feature.chroma_cens(y=y, sr=sr, hop_length=hop_length)


def filter_chroma(chroma: np.ndarray) -> np.ndarray:
    """
    Apply two-stage filtering:

    1. Non-local filtering (nn_filter): suppresses sparse noise by
       comparing each frame with neighbors via cosine similarity.
    2. Temporal median (kernel 9): smooths rapid fluctuations while
       preserving edges (chord transitions).
    """
    filtered = np.minimum(
        chroma,
        librosa.decompose.nn_filter(
            chroma, aggregate=np.median, metric="cosine"
        ),
    )
    filtered = scipy.ndimage.median_filter(filtered, size=(1, 9))
    return filtered


def weight_by_energy(
    chroma: np.ndarray,
    y: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> np.ndarray:
    """
    Weight each chroma frame by the RMS energy of the audio.

    Ensures loud sections (chorus, drops) contribute more to the
    key estimate than silent intros or soft bridges.
    """
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    n = min(chroma.shape[1], len(rms))
    return chroma[:, :n] * rms[:n][np.newaxis, :]


def chroma_pipeline(
    y: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> dict[str, np.ndarray]:
    """
    Full chroma extraction pipeline.

    Returns a dictionary with:
    - 'cqt': filtered and energy-weighted CQT chroma (primary)
    - 'cens': energy-weighted CENS chroma (secondary for ensemble)
    - 'cqt_raw': filtered CQT chroma before energy weighting
    - 'y_harmonic': isolated harmonic signal
    - 'tuning': estimated tuning deviation
    """
    # 1. Aggressive harmonic separation
    y_harmonic = extract_harmonic(y, margin=8)

    # 2. Tuning estimation
    tuning = estimate_tuning(y_harmonic, sr)

    # 3. CQT chroma (primary)
    chroma_cqt = extract_chroma_cqt(y_harmonic, sr, hop_length, tuning)
    chroma_cqt = filter_chroma(chroma_cqt)
    chroma_cqt_weighted = weight_by_energy(chroma_cqt, y, sr, hop_length)

    # 4. CENS chroma (secondary voter)
    chroma_cens = extract_chroma_cens(y_harmonic, sr, hop_length)
    chroma_cens_weighted = weight_by_energy(chroma_cens, y, sr, hop_length)

    return {
        "cqt": chroma_cqt_weighted,
        "cens": chroma_cens_weighted,
        "cqt_raw": chroma_cqt,
        "y_harmonic": y_harmonic,
        "tuning": tuning,
    }
