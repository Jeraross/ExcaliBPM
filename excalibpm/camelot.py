"""
Camelot Wheel for harmonic compatibility in DJ mixing.

The Camelot system encodes the 24 keys into an alphanumeric code
(1A-12A for minors, 1B-12B for majors) where compatible keys are
±1 position on the wheel or the same position with a different letter.
"""

# Mapping: Musical Key → Camelot Code
KEY_TO_CAMELOT: dict[str, str] = {
    "C Major": "8B",   "G Major": "9B",   "D Major": "10B",  "A Major": "11B",
    "E Major": "12B",  "B Major": "1B",   "F# Major": "2B",  "C# Major": "3B",
    "G# Major": "4B",  "D# Major": "5B",  "A# Major": "6B",  "F Major": "7B",
    "A Minor": "8A",   "E Minor": "9A",   "B Minor": "10A",  "F# Minor": "11A",
    "C# Minor": "12A", "G# Minor": "1A",  "D# Minor": "2A",  "A# Minor": "3A",
    "F Minor": "4A",   "C Minor": "5A",   "G Minor": "6A",   "D Minor": "7A",
}

# Reverse mapping
CAMELOT_TO_KEY: dict[str, str] = {v: k for k, v in KEY_TO_CAMELOT.items()}

# Open Key mapping (alternative notation used by some software)
KEY_TO_OPENKEY: dict[str, str] = {
    "C Major": "1d",   "G Major": "2d",   "D Major": "3d",   "A Major": "4d",
    "E Major": "5d",   "B Major": "6d",   "F# Major": "7d",  "C# Major": "8d",
    "G# Major": "9d",  "D# Major": "10d", "A# Major": "11d", "F Major": "12d",
    "A Minor": "1m",   "E Minor": "2m",   "B Minor": "3m",   "F# Minor": "4m",
    "C# Minor": "5m",  "G# Minor": "6m",  "D# Minor": "7m",  "A# Minor": "8m",
    "F Minor": "9m",   "C Minor": "10m",  "G Minor": "11m",  "D Minor": "12m",
}


def get_camelot(key: str) -> str | None:
    """Return the Camelot code for a given musical key."""
    return KEY_TO_CAMELOT.get(key)


def get_openkey(key: str) -> str | None:
    """Return the Open Key code for a given musical key."""
    return KEY_TO_OPENKEY.get(key)


def _circular_distance(a: int, b: int, modulo: int = 12) -> int:
    """Minimum distance between two numbers on a circular ring."""
    diff = abs(a - b)
    return min(diff, modulo - diff)


def compatibility(key_a: str, key_b: str) -> dict:
    """
    Check harmonic compatibility between two musical keys.

    Returns a dictionary with:
    - level: 'perfect' | 'good' | 'risky' | 'incompatible'
    - description: human-readable explanation
    - camelot_a / camelot_b: Camelot codes
    - distance: distance on the wheel (0-6)
    """
    code_a = KEY_TO_CAMELOT.get(key_a)
    code_b = KEY_TO_CAMELOT.get(key_b)

    if code_a is None or code_b is None:
        return {
            "level": "unknown",
            "description": f"Unrecognized key: {key_a if code_a is None else key_b}",
            "camelot_a": code_a,
            "camelot_b": code_b,
            "distance": -1,
        }

    num_a, letter_a = int(code_a[:-1]), code_a[-1]
    num_b, letter_b = int(code_b[:-1]), code_b[-1]
    dist = _circular_distance(num_a, num_b)

    # Exact same key
    if code_a == code_b:
        level, desc = "perfect", "Same key"
    # Same number, different letter (relative major/minor)
    elif num_a == num_b and letter_a != letter_b:
        level, desc = "perfect", "Relative major/minor"
    # Wheel neighbors (±1, same letter)
    elif dist == 1 and letter_a == letter_b:
        level, desc = "good", "Camelot wheel neighbor (±1)"
    # Cross neighbors (±1, different letter)
    elif dist == 1 and letter_a != letter_b:
        level, desc = "good", "Cross neighbor on Camelot wheel"
    # Distance 2 — can work with care
    elif dist == 2:
        level, desc = "risky", "Distance 2 — works with care"
    # Energy jump of 7 semitones (advanced technique)
    elif dist == 7:
        level, desc = "risky", "Energy jump (+7) — advanced technique"
    else:
        level, desc = "incompatible", f"Large harmonic distance ({dist})"

    return {
        "level": level,
        "description": desc,
        "camelot_a": code_a,
        "camelot_b": code_b,
        "distance": dist,
    }


def suggest_next(key: str) -> list[dict]:
    """
    Suggest compatible keys for harmonic transitions.

    Returns a list ordered by compatibility (perfect → good).
    """
    code = KEY_TO_CAMELOT.get(key)
    if code is None:
        return []

    num, letter = int(code[:-1]), code[-1]
    other_letter = "A" if letter == "B" else "B"

    suggestions = []

    # Relative major/minor (same number, different letter)
    relative_code = f"{num}{other_letter}"
    if relative_code in CAMELOT_TO_KEY:
        suggestions.append({
            "key": CAMELOT_TO_KEY[relative_code],
            "camelot": relative_code,
            "level": "perfect",
            "description": "Relative major/minor",
        })

    # Wheel neighbors (±1, same letter)
    for delta in [-1, 1]:
        neighbor_num = ((num - 1 + delta) % 12) + 1
        neighbor_code = f"{neighbor_num}{letter}"
        if neighbor_code in CAMELOT_TO_KEY:
            suggestions.append({
                "key": CAMELOT_TO_KEY[neighbor_code],
                "camelot": neighbor_code,
                "level": "good",
                "description": f"Neighbor {'above' if delta == 1 else 'below'}",
            })

    # Cross neighbors (±1, different letter)
    for delta in [-1, 1]:
        neighbor_num = ((num - 1 + delta) % 12) + 1
        neighbor_code = f"{neighbor_num}{other_letter}"
        if neighbor_code in CAMELOT_TO_KEY:
            suggestions.append({
                "key": CAMELOT_TO_KEY[neighbor_code],
                "camelot": neighbor_code,
                "level": "good",
                "description": f"Cross neighbor {'above' if delta == 1 else 'below'}",
            })

    return suggestions
