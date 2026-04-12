"""
Main analysis orchestrator.

Coordinates all modules (chroma, key_detect, bpm, camelot) to
produce a complete and robust analysis of an audio track.

The Spotify integration (spotify.py) is imported lazily inside analyze()
so that users who do not need Spotify never encounter spotdl import errors.
"""

from __future__ import annotations

import numpy as np
import librosa
import concurrent.futures
from typing import Callable, Union

from .chroma import chroma_pipeline
from .key_detect import (
    ensemble_vote,
    frame_vote,
    analyze_bass_register,
    disambiguate_result,
)
from .bpm import detect_bpm
from .models import MusicAnalysis


def analyze_track(
    audio_path: str,
    segment_duration: float = 30.0,
    sr: int = 22050,
) -> MusicAnalysis:
    """
    Full analysis of an audio track.

    Pipeline:
    1. Load audio and separate harmonic/percussive components
    2. Extract CQT+CENS chroma with filtering and energy weighting
    3. Detect key via ensemble of 8 profiles
    4. Frame-by-frame voting for robustness
    5. Endpoint analysis (start and end of track)
    6. Bass register analysis for disambiguation
    7. Combine all evidence
    8. BPM detection via percussive signal

    Parameters
    ----------
    audio_path : str
        Path to the audio file (wav, mp3, flac, ogg, etc.)
    segment_duration : float
        Seconds used for start/end analysis (default: 30s)
    sr : int
        Sample rate (22050 is sufficient for tonal analysis)
    """
    # ── 1. Load audio ────────────────────────────────────────────
    y, sr = librosa.load(audio_path, sr=sr)
    duration = librosa.get_duration(y=y, sr=sr)

    # ── 2. Harmonic/percussive separation ────────────────────────
    y_harmonic, y_percussive = librosa.effects.hpss(y)

    # ── 3. Chroma pipeline (CQT + CENS) ─────────────────────────
    chroma_data = chroma_pipeline(y, sr, hop_length=512)
    chroma_cqt = chroma_data["cqt"]
    chroma_cens = chroma_data["cens"]

    # RMS for silence filtering in frame voting
    rms = librosa.feature.rms(y=y, hop_length=512)[0]

    # ── 4. Slice start and end segments ─────────────────────────
    max_segment = min(segment_duration, duration * 0.3)
    frames_segment = int(max_segment * sr / 512)

    chroma_start = chroma_cqt[:, :frames_segment]
    chroma_end = chroma_cqt[:, -frames_segment:]

    # ── 5. Concurrent analysis ───────────────────────────────────
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        # BPM (uses percussive signal)
        fut_bpm = executor.submit(detect_bpm, y, sr, y_percussive)

        # Global ensemble (CQT)
        mean_cqt = np.mean(chroma_cqt, axis=1)
        fut_global_cqt = executor.submit(ensemble_vote, mean_cqt)

        # Global ensemble (CENS) — second voter
        mean_cens = np.mean(chroma_cens, axis=1)
        fut_global_cens = executor.submit(ensemble_vote, mean_cens)

        # Frame voting
        fut_frames = executor.submit(
            frame_vote, chroma_cqt, sr, 512, 4.0, rms
        )

        # Endpoints
        mean_start = np.mean(chroma_start, axis=1)
        fut_start = executor.submit(ensemble_vote, mean_start)

        mean_end = np.mean(chroma_end, axis=1)
        fut_end = executor.submit(ensemble_vote, mean_end)

        # Bass register
        y_harm_full = chroma_data["y_harmonic"]
        fut_bass = executor.submit(analyze_bass_register, y_harm_full, sr, 512)

        # Collect results
        bpm = fut_bpm.result()
        res_global_cqt = fut_global_cqt.result()
        res_global_cens = fut_global_cens.result()
        res_frames = fut_frames.result()
        res_start = fut_start.result()
        res_end = fut_end.result()
        bass_chroma = fut_bass.result()

    # ── 6. Meta-ensemble: combine CQT and CENS ──────────────────
    # If CQT and CENS agree, confidence is high.
    # If they disagree, frame voting decides.
    if res_global_cqt.key == res_global_cens.key:
        res_global = res_global_cqt
        res_global.confidence = min(1.0, res_global.confidence * 1.2)
    elif res_global_cqt.key == res_frames.key:
        res_global = res_global_cqt
    elif res_global_cens.key == res_frames.key:
        res_global = res_global_cens
    else:
        # No agreement — use CQT as primary
        res_global = res_global_cqt

    # ── 7. Final disambiguation ──────────────────────────────────
    result = disambiguate_result(
        global_result=res_global,
        frame_result=res_frames,
        start_result=res_start,
        end_result=res_end,
        bass_chroma=bass_chroma,
    )

    # ── 8. Build final result ────────────────────────────────────
    return MusicAnalysis(
        key=result.key,
        key_confidence=result.confidence,
        key_start=res_start.key,
        start_confidence=res_start.confidence,
        key_end=res_end.key,
        end_confidence=res_end.confidence,
        bpm=bpm,
        duration_seconds=duration,
        file=audio_path,
        profile_votes=result.profile_votes,
        frame_votes=result.frame_votes or [],
    )


def analyze_batch(
    paths: list[str],
    sr: int = 22050,
    spotify_config=None,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> list[MusicAnalysis]:
    """
    Analyze multiple tracks sequentially. Accepts mixed inputs (file paths
    and Spotify URLs).

    For true inter-track parallelism, use ProcessPoolExecutor
    externally (each track already uses threads internally).
    """
    results = []
    total = len(paths)
    for i, path in enumerate(paths):
        if on_progress:
            on_progress(f"Analyzing {i + 1}/{total}: {path}", i, total)
        try:
            r = analyze(path, spotify_config=spotify_config)
            if isinstance(r, list):
                results.extend(r)
            else:
                results.append(r)
        except Exception as e:
            print(f"  ERROR in {path}: {e}")
    return results


def analyze(
    input: str,
    spotify_config=None,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> Union[MusicAnalysis, list[MusicAnalysis]]:
    """
    Smart input router: analyze a local file or a Spotify URL.

    - Local file path → calls analyze_track() directly.
    - Spotify track URL → downloads, analyzes, cleans up; returns MusicAnalysis.
    - Spotify album/playlist URL → downloads all tracks, returns list[MusicAnalysis].

    The on_progress callback receives (message, current, total).

    spotify_config is a SpotifyConfig instance (or None for defaults).
    Spotify dependencies (spotdl, ffmpeg) are only required when a Spotify
    URL is passed — local file analysis never needs them.
    """
    import os

    # Lazy import: spotify.py is never loaded for local-file-only workflows.
    from .spotify import is_spotify_url, SpotifySession, SpotifyConfig

    if not is_spotify_url(input):
        # Local file path
        if on_progress:
            on_progress(f"Analyzing: {input}", 0, 1)
        result = analyze_track(input)
        if on_progress:
            on_progress(f"Done: {input}", 1, 1)
        return result

    # Spotify URL
    config = spotify_config if spotify_config is not None else SpotifyConfig()

    with SpotifySession(config) as session:
        tracks = session.download(input, on_progress=on_progress)

        results = []
        total = len(tracks)
        for i, track in enumerate(tracks):
            if not track.success:
                print(f"  SKIP {track.url}: {track.error}")
                continue
            if on_progress:
                on_progress(
                    f"Analyzing {track.artist} - {track.title}",
                    i, total,
                )
            try:
                r = analyze_track(track.local_path)
                r.spotify_url = track.url
                results.append(r)
            except Exception as e:
                print(f"  ERROR analyzing {track.local_path}: {e}")

    # Classify URL to decide return type
    from .spotify import classify_url
    parsed = classify_url(input)
    url_type = parsed[0] if parsed else "track"

    if url_type == "track":
        return results[0] if results else MusicAnalysis(
            key="Unknown", key_confidence=0.0,
            key_start="Unknown", start_confidence=0.0,
            key_end="Unknown", end_confidence=0.0,
            bpm=0.0, duration_seconds=0.0,
            spotify_url=input,
        )

    return results
