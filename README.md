# ExcaliBPM

A high-precision audio analysis library built to help DJs make better mixing decisions.
Developed by **Jera**.

---

## What It Does

Getting a key detection wrong in a DJ set means a clashing transition in front of a live audience.
ExcaliBPM was built to solve that — combining multiple musicological profiling techniques,
frame-level voting, and harmonic bass analysis to produce accurate key and BPM readings that
DJs can actually trust.

Beyond raw analysis, it speaks the language of DJ software: every result includes
the **Camelot Wheel** position and **Open Key** notation, and the built-in compatibility
engine tells you instantly whether two tracks will blend harmonically.

---

## Detection Techniques

| Technique | Purpose |
|-----------|---------|
| HPSS with `margin=8` | Isolates harmonic content, strips percussion that pollutes the chromagram |
| Chroma CQT (`bins_per_octave=36`) | 3 bins per semitone — better separation between tonic and dominant |
| Automatic tuning correction | Prevents chromatic leakage in slightly detuned recordings |
| Non-local filtering + median smoothing | Removes spectral noise without blurring real transitions |
| RMS energy weighting | Choruses carry more weight than silent intros |
| 8-profile ensemble voting | Krumhansl-Schmuckler, Temperley, Bellman-Budge, Aarden, and more |
| Frame-by-frame voting (~4s windows) | Robust against modulations and mid-song key changes |
| Bass register analysis | Disambiguates parallel keys such as C Major vs A Minor |
| Endpoint analysis | Start and end sections reinforce tonic identification |
| CQT + CENS meta-ensemble | Two chroma representations vote together for a final answer |

---

## Project Structure

```
ExcaliBPM/
<<<<<<< HEAD
├── .github/
│   ├── labeler.yml
│   └── workflows/
│       ├── auto-label.yml      # Automatic PR labeling
│       ├── benchmark.yml       # Performance regression check on PRs
│       ├── ci.yml              # Lint + test matrix (Python 3.10–3.12)
│       ├── release.yml         # GitHub Release on version tags
│       ├── security.yml        # CodeQL static analysis
│       └── stale.yml           # Auto-close inactive issues/PRs
├── Musics/                     # Sample audio files for manual testing
│   ├── Runaway.wav
│   ├── notRight.wav
│   └── theSpins.wav
├── excalibpm/                  # Core package
=======
├── music_analyzer/             # Core package
>>>>>>> 9932ac9735cfcfcc5e731226979777c2647b8ec4
│   ├── __init__.py             # Public API
│   ├── core.py                 # Main orchestrator
│   ├── chroma.py               # Chromagram extraction pipeline
│   ├── key_detect.py           # Key detection algorithms
│   ├── bpm.py                  # BPM detection
│   ├── camelot.py              # Camelot Wheel + compatibility engine
│   ├── models.py               # Result dataclasses
│   └── profiles.py             # 8 key profile sets
├── tests/                      # Test suite
│   ├── conftest.py             # Shared fixtures (synthetic chroma, sample analysis)
│   ├── test_bpm.py
│   ├── test_camelot.py
│   ├── test_key_detect.py
│   ├── test_models.py
│   └── test_profiles.py
├── main.py                     # Command-line interface
├── requirements.txt
├── README.md
└── SECURITY.md
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## CLI Usage

```bash
# Basic analysis
python main.py track.wav

# Multiple files, JSON output
python main.py *.mp3 --json

# Check harmonic compatibility between two tracks
python main.py track_a.wav --compatible-with track_b.wav

# Suggest keys for the next track in the set
python main.py track.wav --suggestions

# Debug mode: inspect per-profile votes and frame results
python main.py track.wav --debug
```

---

## Library Usage

```python
from music_analyzer import analyze_track, compatibility, suggest_next

# Full analysis
result = analyze_track("track.wav")
print(result)
print(result.to_dict())  # Ready for JSON / API responses

# Check compatibility for a transition
track_a = analyze_track("track_a.wav")
track_b = analyze_track("track_b.wav")

compat = compatibility(track_a.key_end, track_b.key_start)
print(compat)
# {'level': 'good', 'description': 'Camelot wheel neighbor (±1)', ...}

# Suggest what to play next
suggestions = suggest_next(track_a.key)
for s in suggestions:
    print(f"{s['camelot']}  {s['key']}  —  {s['level']}")
```

---

## Output Example

```
════════════════════════════════════════════════════════
  MUSIC ANALYSIS
  theSpins.wav
════════════════════════════════════════════════════════
  Duration       : 3:15
  BPM            : 126.0
────────────────────────────────────────────────────────
  Overall Key    : A Minor        │ 8A   │ 75%
  Start Key      : A Minor        │ 8A   │ 62%
  End Key        : A Minor        │ 8A   │ 68%
════════════════════════════════════════════════════════
```

---

## Mixing Integration

`to_dict()` returns a JSON-ready dictionary for use in APIs and external tools:

```python
import json
result = analyze_track("track.wav")
print(json.dumps(result.to_dict(), indent=2))
```

```json
{
  "file": "track.wav",
  "bpm": 126.0,
  "key": "A Minor",
  "camelot": "8A",
  "openkey": "1m",
  "key_confidence": 0.75,
  "key_start": "A Minor",
  "key_end": "A Minor"
}
```

To evaluate whether two tracks will transition cleanly, compare the **end key**
of the outgoing track against the **start key** of the incoming one:

```python
compat = compatibility(outgoing.key_end, incoming.key_start)
if compat["level"] in ("perfect", "good"):
    print("Safe harmonic transition.")
```

---

## Author

Developed by [Jeronimo Rossi](https://github.com/Jeraross).  
Built for DJs who care about the details.
