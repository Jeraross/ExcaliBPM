# Music Analyzer

A high-precision audio analysis library built to help DJs make better mixing decisions.
Developed by **Jera**.

---

## What It Does

Getting a key detection wrong in a DJ set means a clashing transition in front of a live audience.
This library was built to solve that — combining multiple musicological profiling techniques,
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
music_analyzer/
├── main.py                 # Command-line interface
├── requirements.txt
├── README.md
└── music_analyzer/
    ├── __init__.py         # Public API
    ├── core.py             # Main orchestrator
    ├── chroma.py           # Chromagram extraction
    ├── key_detect.py       # Key detection algorithms
    ├── bpm.py              # BPM detection
    ├── camelot.py          # Camelot Wheel + compatibility engine
    ├── models.py           # Result dataclasses
    └── profiles.py         # 8 tonality profile sets
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
from music_analyzer import analisar_musica, compatibilidade, sugerir_proximas

# Full analysis
result = analisar_musica("track.wav")
print(result)
print(result.to_dict())  # Ready for JSON / API responses

# Check compatibility for a transition
track_a = analisar_musica("track_a.wav")
track_b = analisar_musica("track_b.wav")

compat = compatibilidade(track_a.tonalidade_final, track_b.tonalidade_inicio)
print(compat)
# {'nivel': 'boa', 'descricao': 'Neighbor on the Camelot Wheel (+1)', ...}

# Suggest what to play next
suggestions = sugerir_proximas(track_a.tonalidade_geral)
for s in suggestions:
    print(f"{s['camelot']}  {s['tom']}  —  {s['nivel']}")
```

---

## Output Example

```
════════════════════════════════════════════════════════
  ANALYSIS RESULT
  theSpins.wav
════════════════════════════════════════════════════════
  Duration       : 3:15
  BPM            : 126.0
────────────────────────────────────────────────────────
  Overall Key    : A Minor        │ 8A   │ 75%
  Opening Key    : A Minor        │ 8A   │ 62%
  Closing Key    : A Minor        │ 8A   │ 68%
════════════════════════════════════════════════════════
```

---

## Mixing Integration

`to_dict()` returns a JSON-ready dictionary for use in APIs and external tools:

```python
import json
result = analisar_musica("track.wav")
print(json.dumps(result.to_dict(), indent=2))
```

```json
{
  "arquivo": "track.wav",
  "bpm": 126.0,
  "tonalidade_geral": "A Minor",
  "camelot": "8A",
  "openkey": "1m",
  "confianca_geral": 0.75,
  "tonalidade_inicio": "A Minor",
  "tonalidade_final": "A Minor"
}
```

To evaluate whether two tracks will transition cleanly, compare the **closing key**
of the outgoing track against the **opening key** of the incoming one:

```python
compat = compatibilidade(outgoing.tonalidade_final, incoming.tonalidade_inicio)
if compat["nivel"] in ("perfeita", "boa"):
    print("Safe harmonic transition.")
```

---

## Author

Developed by [Jeronimo Rossi](https://github.com/Jeraross).  
Built for DJs who care about the details.
