"""
Musical key detection engine.

Combines multiple strategies for maximum accuracy:
1. Pearson correlation with 7 profile sets
2. Ensemble voting (majority across profiles)
3. Frame-by-frame voting (~4s segments)
4. Endpoint analysis (start/end of track)
5. Bass register analysis for tonic disambiguation
"""

import numpy as np
from collections import Counter
from dataclasses import dataclass

from .profiles import get_all_profiles

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Relative key relationships (major → relative minor)
_RELATIVES = {
    "C Major": "A Minor", "G Major": "E Minor", "D Major": "B Minor",
    "A Major": "F# Minor", "E Major": "C# Minor", "B Major": "G# Minor",
    "F# Major": "D# Minor", "C# Major": "A# Minor", "G# Major": "F Minor",
    "D# Major": "C Minor", "A# Major": "G Minor", "F Major": "D Minor",
}
_RELATIVES.update({v: k for k, v in _RELATIVES.items()})


@dataclass
class KeyResult:
    """Detailed result from key detection."""
    key: str
    confidence: float
    correlations: dict[str, float]
    profile_votes: dict[str, str]
    frame_votes: list[str] | None = None


def _pearson_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson correlation between two vectors."""
    x_c = x - np.mean(x)
    y_c = y - np.mean(y)
    num = np.dot(x_c, y_c)
    den = np.linalg.norm(x_c) * np.linalg.norm(y_c)
    if den < 1e-12:
        return 0.0
    return num / den


def _euclidean_similarity(x: np.ndarray, y: np.ndarray) -> float:
    """Similarity based on Euclidean distance (inverted)."""
    x_n = x / (np.linalg.norm(x) + 1e-12)
    y_n = y / (np.linalg.norm(y) + 1e-12)
    dist = np.linalg.norm(x_n - y_n)
    return 1.0 / (1.0 + dist)


def detect_with_profile(
    chroma_vec: np.ndarray,
    profile_major: np.ndarray,
    profile_minor: np.ndarray,
    use_euclidean: bool = False,
) -> tuple[str, float, dict[str, float]]:
    """
    K-S detection with a single profile pair.

    Tests all 24 possible keys (12 major + 12 minor) by rotating
    the profiles and computing correlation against the chroma vector.
    """
    func = _euclidean_similarity if use_euclidean else _pearson_correlation
    correlations: dict[str, float] = {}

    for i in range(12):
        major_rot = np.roll(profile_major, i)
        minor_rot = np.roll(profile_minor, i)

        correlations[f"{NOTES[i]} Major"] = func(chroma_vec, major_rot)
        correlations[f"{NOTES[i]} Minor"] = func(chroma_vec, minor_rot)

    ranking = sorted(correlations.items(), key=lambda x: x[1], reverse=True)
    best_key, best_corr = ranking[0]
    second_corr = ranking[1][1]

    # Confidence: relative distance between 1st and 2nd place
    gap = best_corr - second_corr
    confidence = min(1.0, max(0.0, gap / (abs(best_corr) + 1e-10) * 3.0))

    return best_key, confidence, correlations


def ensemble_vote(
    chroma_vec: np.ndarray,
    profiles: dict[str, dict[str, np.ndarray]] | None = None,
) -> KeyResult:
    """
    Ensemble voting: each profile set votes independently,
    and the most-voted key wins. Ties are broken by highest
    average correlation.
    """
    if profiles is None:
        profiles = get_all_profiles()

    votes: list[str] = []
    votes_by_profile: dict[str, str] = {}
    all_correlations: dict[str, list[float]] = {}

    for name, modes in profiles.items():
        use_euc = name == "albrecht_shanahan"
        key, conf, corrs = detect_with_profile(
            chroma_vec, modes["major"], modes["minor"], use_euclidean=use_euc
        )
        votes.append(key)
        votes_by_profile[name] = key

        for k, v in corrs.items():
            all_correlations.setdefault(k, []).append(v)

    # Average correlation per key (used for tie-breaking)
    avg_corr = {k: np.mean(v) for k, v in all_correlations.items()}

    count = Counter(votes)
    max_votes = count.most_common(1)[0][1]
    tied = [k for k, c in count.items() if c == max_votes]

    if len(tied) == 1:
        winner = tied[0]
    else:
        # Tie-break by highest average correlation
        winner = max(tied, key=lambda k: avg_corr.get(k, 0))

    # Ensemble confidence: proportion of votes for the winner
    confidence = max_votes / len(votes)

    return KeyResult(
        key=winner,
        confidence=confidence,
        correlations=avg_corr,
        profile_votes=votes_by_profile,
    )


def frame_vote(
    chroma: np.ndarray,
    sr: int,
    hop_length: int = 512,
    segment_duration: float = 4.0,
    rms: np.ndarray | None = None,
    silence_threshold: float = 0.01,
) -> KeyResult:
    """
    Split the chroma matrix into ~4s segments, detect the key of each,
    and vote by majority. Silent segments are discarded.

    More robust than a global average because long modulations or
    bridges do not distort the result.
    """
    frames_per_segment = int(segment_duration * sr / hop_length)
    total_frames = chroma.shape[1]
    profiles = get_all_profiles()

    votes: list[str] = []

    for start in range(0, total_frames - frames_per_segment // 2, frames_per_segment):
        end = min(start + frames_per_segment, total_frames)
        segment = chroma[:, start:end]

        # Filter silence
        if rms is not None:
            rms_seg = rms[start:min(end, len(rms))]
            if len(rms_seg) > 0 and np.mean(rms_seg) < silence_threshold:
                continue

        chroma_mean = np.mean(segment, axis=1)
        if np.linalg.norm(chroma_mean) < 1e-10:
            continue

        result = ensemble_vote(chroma_mean, profiles)
        votes.append(result.key)

    if not votes:
        return KeyResult(
            key="Undetermined", confidence=0.0,
            correlations={}, profile_votes={}, frame_votes=votes,
        )

    count = Counter(votes)
    winner, n_votes = count.most_common(1)[0]
    confidence = n_votes / len(votes)

    return KeyResult(
        key=winner, confidence=confidence,
        correlations={}, profile_votes={}, frame_votes=votes,
    )


def analyze_bass_register(
    y: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> np.ndarray:
    """
    Extract chroma only from the bass register (< ~300 Hz).

    The most frequent note in the bass at cadential points is very
    likely the tonic. Helps disambiguate C Major vs A Minor.
    """
    import librosa

    # CQT limited to the bass register (C1 to D#3 ≈ 32-311 Hz)
    S = np.abs(librosa.cqt(
        y=y, sr=sr, hop_length=hop_length,
        fmin=librosa.note_to_hz("C1"),
        n_bins=36,  # 3 octaves × 12 bins
        bins_per_octave=12,
    ))

    # Map to 12 pitch classes (bass chroma)
    bass_chroma = np.zeros((12, S.shape[1]))
    for i in range(S.shape[0]):
        bass_chroma[i % 12] += S[i]

    return bass_chroma


def disambiguate_result(
    global_result: KeyResult,
    frame_result: KeyResult,
    start_result: KeyResult,
    end_result: KeyResult,
    bass_chroma: np.ndarray | None = None,
) -> KeyResult:
    """
    Combine all evidence to produce the final result.

    Weights:
    - Global ensemble:  3 votes
    - Frame voting:     3 votes
    - Track start:      1 vote
    - Track end:        2 votes (ending is a stronger tonic indicator)
    - Bass register:    1 vote  (if available)
    """
    weighted_votes: list[str] = []

    weighted_votes.extend([global_result.key] * 3)
    weighted_votes.extend([frame_result.key] * 3)
    weighted_votes.extend([start_result.key] * 1)
    weighted_votes.extend([end_result.key] * 2)

    # Bass as tie-breaker
    if bass_chroma is not None:
        bass_sum = np.sum(bass_chroma, axis=1)
        bass_note_idx = int(np.argmax(bass_sum))
        # Vote for the key whose tonic matches the dominant bass note
        weighted_votes.append(f"{NOTES[bass_note_idx]} Major")
        weighted_votes.append(f"{NOTES[bass_note_idx]} Minor")

    count = Counter(weighted_votes)
    candidates = count.most_common(4)

    winner = candidates[0][0]
    total = sum(c for _, c in candidates)
    confidence = candidates[0][1] / total

    # If the top two candidates are relatives (e.g. C Major and A Minor),
    # use the bass and endpoints to decide
    if len(candidates) >= 2:
        second = candidates[1][0]
        if _RELATIVES.get(winner) == second or _RELATIVES.get(second) == winner:
            points_winner = 0
            points_second = 0

            # Endpoints favor the ending (tonal convention: resolve to tonic)
            if end_result.key == winner:
                points_winner += 2
            elif end_result.key == second:
                points_second += 2

            if start_result.key == winner:
                points_winner += 1
            elif start_result.key == second:
                points_second += 1

            # Bass: the tonic should be the most prominent note in the bass
            if bass_chroma is not None:
                bass_sum = np.sum(bass_chroma, axis=1)
                tonic_winner = NOTES.index(winner.split()[0])
                tonic_second = NOTES.index(second.split()[0])
                if bass_sum[tonic_winner] > bass_sum[tonic_second]:
                    points_winner += 1
                else:
                    points_second += 1

            if points_second > points_winner:
                winner = second
                confidence = candidates[1][1] / total

    return KeyResult(
        key=winner,
        confidence=confidence,
        correlations=global_result.correlations,
        profile_votes=global_result.profile_votes,
        frame_votes=frame_result.frame_votes,
    )
