# ExcaliBPM

A high-precision audio analysis library built to help DJs make better mixing decisions.

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
├── excalibpm/                  # Core package
│   ├── __init__.py             # Public API (v2.0.0)
│   ├── core.py                 # Main orchestrator + smart input router
│   ├── chroma.py               # Chromagram extraction pipeline
│   ├── key_detect.py           # Key detection algorithms
│   ├── bpm.py                  # BPM detection
│   ├── camelot.py              # Camelot Wheel + compatibility engine
│   ├── models.py               # Result dataclasses
│   ├── profiles.py             # 8 key profile sets
│   └── spotify.py              # Spotify integration (optional)
├── tests/                      # Test suite
│   ├── conftest.py             # Shared fixtures + spotdl availability check
│   ├── test_bpm.py
│   ├── test_camelot.py
│   ├── test_key_detect.py
│   ├── test_models.py
│   ├── test_profiles.py
│   ├── test_spotify_unit.py    # No network required
│   └── test_spotify_integration.py  # Requires spotdl + ffmpeg + internet
├── main.py                     # Command-line interface
├── requirements.txt            # Core dependencies
├── requirements-spotify.txt    # Optional Spotify dependencies
├── pytest.ini
├── README.md
└── SECURITY.md
```

---

## Installation

```bash
# Core (key + BPM analysis of local files)
pip install -r requirements.txt

# + Spotify integration
pip install -r requirements-spotify.txt   # installs spotdl
# Also requires ffmpeg:
#   Ubuntu/Debian:  sudo apt install ffmpeg
#   macOS:          brew install ffmpeg
#   Windows:        choco install ffmpeg
```

---

## Dependencies

| Dependency | Required? | Purpose |
|------------|-----------|---------|
| librosa, numpy, scipy, soundfile | Always | Core audio analysis |
| spotdl | Spotify only | Download audio from Spotify |
| ffmpeg | Spotify only | Audio format conversion |

Core key/BPM analysis works without spotdl or ffmpeg. Only raise errors
when you actually call `analyze()` with a Spotify URL.

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

## CLI Spotify Examples (W.I.P.)

```bash
# Verify spotdl and ffmpeg are ready
python main.py --check-deps

# Download + analyze a single track (temp mode — auto-deleted after analysis)
python main.py https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC

# Analyze a full playlist, keep a local cache
python main.py https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M \
    --cache-dir /tmp/spotify_cache --json

# Compatibility check: local file vs Spotify URL
python main.py track_a.wav \
    --compatible-with https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC

# Keep downloaded files in a permanent library
python main.py https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3 \
    --keep-downloads --output-dir ~/Music/library

# Show and manage cache
python main.py --cache-info --cache-dir /tmp/spotify_cache
python main.py --cache-clear --cache-dir /tmp/spotify_cache
```

---

## Library Usage

```python
from excalibpm import analyze_track, compatibility, suggest_next

# Full analysis of a local file
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

## Spotify Integration (W.I.P.)

> **Requires:** `pip install spotdl` and `ffmpeg` in your PATH.

```python
from excalibpm import analyze, SpotifyConfig

# Single track — returns MusicAnalysis
result = analyze("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
print(result.key, result.bpm, result.camelot)

# Playlist — returns list[MusicAnalysis]
results = analyze("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M")
for r in results:
    print(r.key, r.bpm, r.spotify_url)

# With SpotifyConfig (cache mode)
config = SpotifyConfig(cache_dir="/tmp/spotify_cache", cache_max_mb=1000)
result = analyze(
    "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
    spotify_config=config,
)

# With progress callback
def on_progress(msg, current, total):
    print(f"[{current}/{total}] {msg}")

result = analyze(
    "https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3",
    on_progress=on_progress,
)
```

---

## Storage Modes

| Mode | How to enable | Behavior |
|------|--------------|----------|
| **Temp** (default) | `SpotifyConfig()` | Downloads to a tmpdir, deleted on exit. Zero disk footprint. |
| **Cache** | `SpotifyConfig(cache_dir="/path")` | Persistent LRU cache. Skip download on hit. Configurable size limit. |
| **Keep** | `SpotifyConfig(keep_files=True, output_dir="/path")` | Download to output_dir, never delete. Build a local library. |

Use **temp mode** for one-off analysis. Use **cache mode** when you repeatedly
analyze the same tracks. Use **keep mode** to build a permanent local library.

---

> **Disclaimer:** Downloading copyrighted content may violate the Spotify Terms
> of Service. This tool is intended for educational purposes. Support artists by
> purchasing their music.

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
