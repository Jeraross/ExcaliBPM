"""
ExcaliBPM — Robust key and BPM detection for DJ mixing.

Quick usage:
    from music_analyzer import analyze_track, compatibility, suggest_next

    result = analyze_track("track.wav")
    print(result)

    compat = compatibility(result.key, "A Minor")
    print(compat)
"""

from .core import analyze_track, analyze_batch
from .models import MusicAnalysis
from .camelot import compatibility, suggest_next, get_camelot, get_openkey

__all__ = [
    "analyze_track",
    "analyze_batch",
    "MusicAnalysis",
    "compatibility",
    "suggest_next",
    "get_camelot",
    "get_openkey",
]

__version__ = "1.0.0"
