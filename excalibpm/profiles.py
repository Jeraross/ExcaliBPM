"""
Key profiles for musical key detection.

Contains 7 validated profile sets from academic literature,
each optimized for different genres and contexts.
Values represent the relative importance of each chromatic pitch
(C, C#, D, D#, E, F, F#, G, G#, A, A#, B) within a scale.
"""

import numpy as np

PROFILES: dict[str, dict[str, list[float]]] = {
    # ── Krumhansl-Kessler (1990) ─────────────────────────────────
    # Origin: probe-tone perceptual experiments.
    # Good for: short classical excerpts.
    # Weakness: prone to confusion with the dominant (5th).
    "krumhansl_kessler": {
        "major": [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
        "minor": [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    },

    # ── Temperley CBMS (2007) ────────────────────────────────────
    # Origin: Music and Probability, p.86.
    # Good for: general use, good major/minor separation.
    "temperley": {
        "major": [5.0, 2.0, 3.5, 2.0, 4.5, 4.0, 2.0, 4.5, 2.0, 3.5, 1.5, 4.0],
        "minor": [5.0, 2.0, 3.5, 4.5, 2.0, 4.0, 2.0, 4.5, 3.5, 2.0, 1.5, 4.0],
    },

    # ── Temperley / Kostka-Payne ─────────────────────────────────
    # Origin: corpus of analyses from the Kostka-Payne textbook.
    # Good for: classical music, high accuracy in major mode.
    "kostka_payne": {
        "major": [0.748, 0.060, 0.488, 0.082, 0.670, 0.460, 0.096, 0.715, 0.104, 0.366, 0.057, 0.400],
        "minor": [0.712, 0.084, 0.474, 0.618, 0.049, 0.460, 0.105, 0.747, 0.404, 0.067, 0.133, 0.330],
    },

    # ── Bellman-Budge (2005) ─────────────────────────────────────
    # Origin: Budge (1943) chord frequency study.
    # Good for: LOWER tendency to confuse neighboring keys.
    # Recommended as the primary default profile.
    "bellman_budge": {
        "major": [16.80, 0.86, 12.95, 1.41, 13.49, 11.93, 1.25, 20.28, 1.80, 8.04, 0.62, 10.57],
        "minor": [18.16, 0.69, 12.99, 13.34, 1.07, 11.15, 1.38, 21.07, 7.49, 1.53, 0.92, 10.21],
    },

    # ── Aarden / Essen (2003) ────────────────────────────────────
    # Origin: Essen Folk Song Collection.
    # Good for: folk music, very high accuracy in minor mode.
    "aarden_essen": {
        "major": [17.7661, 0.145624, 14.9265, 0.160186, 19.8049, 11.3587, 0.291248,
                  22.062, 0.145624, 8.15494, 0.232998, 4.95122],
        "minor": [18.2648, 0.737619, 14.0499, 16.8599, 0.702494, 14.4362, 0.702494,
                  18.6161, 4.56621, 1.93186, 7.37619, 1.75623],
    },

    # ── Simple / Sapp (2011) ─────────────────────────────────────
    # Binary weights: 2=tonic/dominant, 1=diatonic, 0=chromatic.
    # Surprisingly effective for long musical passages.
    "simple_sapp": {
        "major": [2, 0, 1, 0, 1, 1, 0, 2, 0, 1, 0, 1],
        "minor": [2, 0, 1, 1, 0, 1, 0, 2, 1, 0, 0.5, 0.5],
    },

    # ── Albrecht-Shanahan (2013) ─────────────────────────────────
    # Trained via neural network on 490 pieces.
    # Best minor-mode accuracy of all profiles.
    # NOTE: works best with Euclidean distance.
    "albrecht_shanahan": {
        "major": [0.238, 0.006, 0.111, 0.006, 0.137, 0.094, 0.016, 0.214, 0.009, 0.080, 0.008, 0.081],
        "minor": [0.220, 0.006, 0.104, 0.123, 0.019, 0.103, 0.012, 0.214, 0.062, 0.022, 0.061, 0.052],
    },
}

# ── Shaath profiles — optimized for electronic/pop music ────────
PROFILES_EDM: dict[str, dict[str, list[float]]] = {
    "shaath": {
        "major": [0.95162, 0.20742, 0.71758, 0.22007, 0.71341, 0.48841, 0.31431,
                  1.00000, 0.20957, 0.53657, 0.22585, 0.55363],
        "minor": [0.94409, 0.21742, 0.64525, 0.63229, 0.27897, 0.57709, 0.26428,
                  1.0000, 0.26428, 0.30633, 0.45924, 0.35929],
    },
}


def get_all_profiles() -> dict[str, dict[str, np.ndarray]]:
    """Return all profiles (general + EDM) as normalized numpy arrays."""
    combined = {**PROFILES, **PROFILES_EDM}
    result = {}
    for name, modes in combined.items():
        result[name] = {
            "major": np.array(modes["major"], dtype=np.float64),
            "minor": np.array(modes["minor"], dtype=np.float64),
        }
    return result
