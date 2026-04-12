"""
ExcaliBPM — Robust key and BPM detection for DJ mixing.

Quick usage (local files):
    from excalibpm import analyze_track, compatibility, suggest_next

    result = analyze_track("track.wav")
    print(result)

    compat = compatibility(result.key, "A Minor")
    print(compat)

Spotify usage (requires spotdl + ffmpeg):
    from excalibpm import analyze, SpotifyConfig

    result = analyze("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
    print(result)

    # Playlist → returns list[MusicAnalysis]
    results = analyze(
        "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        spotify_config=SpotifyConfig(cache_dir="/tmp/spotify_cache"),
    )
"""

from .core import analyze_track, analyze_batch, analyze
from .models import MusicAnalysis
from .camelot import compatibility, suggest_next, get_camelot, get_openkey

# Spotify exports — imported lazily so they don't require spotdl at import time.
# Importing them here pulls in spotify.py but does NOT require spotdl to be
# installed (spotdl is only needed when you call download/session methods).
from .spotify import (
    SpotifyConfig,
    SpotifySession,
    SpotifyTrackInfo,
    is_spotify_url,
    check_dependencies,
    download_spotify,
    classify_url,
)

__all__ = [
    # Core analysis
    "analyze_track",
    "analyze_batch",
    "analyze",
    # Models
    "MusicAnalysis",
    # Camelot
    "compatibility",
    "suggest_next",
    "get_camelot",
    "get_openkey",
    # Spotify
    "SpotifyConfig",
    "SpotifySession",
    "SpotifyTrackInfo",
    "is_spotify_url",
    "check_dependencies",
    "download_spotify",
    "classify_url",
]

__version__ = "2.0.0"
