"""
Data models for music analysis results.
"""

from dataclasses import dataclass, field
from .camelot import get_camelot, get_openkey


@dataclass
class MusicAnalysis:
    """Complete analysis result for a single audio track."""

    # Overall key
    key: str
    key_confidence: float

    # Key at the start of the track
    key_start: str
    start_confidence: float

    # Key at the end of the track
    key_end: str
    end_confidence: float

    # BPM
    bpm: float

    # Metadata
    duration_seconds: float
    file: str = ""

    # Vote details (for debugging)
    profile_votes: dict[str, str] = field(default_factory=dict)
    frame_votes: list[str] = field(default_factory=list)

    @property
    def camelot(self) -> str:
        return get_camelot(self.key) or "?"

    @property
    def openkey(self) -> str:
        return get_openkey(self.key) or "?"

    @property
    def camelot_start(self) -> str:
        return get_camelot(self.key_start) or "?"

    @property
    def camelot_end(self) -> str:
        return get_camelot(self.key_end) or "?"

    def __str__(self) -> str:
        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)

        lines = [
            f"{'═' * 56}",
            "  MUSIC ANALYSIS",
            f"  {self.file}" if self.file else "",
            f"{'═' * 56}",
            f"  Duration       : {minutes}:{seconds:02d}",
            f"  BPM            : {self.bpm:.1f}",
            f"{'─' * 56}",
            f"  Overall Key    : {self.key:<14} │ {self.camelot:<4} │ {self.key_confidence:.0%}",
            f"  Start Key      : {self.key_start:<14} │ {self.camelot_start:<4} │ {self.start_confidence:.0%}",
            f"  End Key        : {self.key_end:<14} │ {self.camelot_end:<4} │ {self.end_confidence:.0%}",
            f"{'═' * 56}",
        ]
        return "\n".join(line for line in lines if line)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "file": self.file,
            "duration_seconds": round(self.duration_seconds, 2),
            "bpm": self.bpm,
            "key": self.key,
            "camelot": self.camelot,
            "openkey": self.openkey,
            "key_confidence": round(self.key_confidence, 4),
            "key_start": self.key_start,
            "camelot_start": self.camelot_start,
            "start_confidence": round(self.start_confidence, 4),
            "key_end": self.key_end,
            "camelot_end": self.camelot_end,
            "end_confidence": round(self.end_confidence, 4),
        }
