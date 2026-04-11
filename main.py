#!/usr/bin/env python3
"""
CLI for music analysis.

Usage:
    python main.py track.wav
    python main.py track1.mp3 track2.flac --json
    python main.py track_a.wav --compatible-with track_b.wav
"""

import argparse
import json
import sys
import os

from music_analyzer import (
    analyze_track,
    compatibility,
    suggest_next,
)


def main():
    parser = argparse.ArgumentParser(
        description="ExcaliBPM — Robust music analysis: key, BPM, and Camelot compatibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py track.wav
  python main.py *.mp3 --json
  python main.py track_a.wav --compatible-with track_b.wav
  python main.py track.wav --suggestions
        """,
    )

    parser.add_argument(
        "files",
        nargs="+",
        help="Audio file(s) to analyze",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--compatible-with",
        metavar="FILE",
        help="Check harmonic compatibility with another file",
    )
    parser.add_argument(
        "--suggestions",
        action="store_true",
        help="Show compatible keys for transition (Camelot)",
    )
    parser.add_argument(
        "--sr",
        type=int,
        default=22050,
        help="Sample rate (default: 22050)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show detailed votes from each profile",
    )

    args = parser.parse_args()

    results = []

    for file in args.files:
        if not os.path.exists(file):
            print(f"File not found: {file}", file=sys.stderr)
            continue

        print(f"\nAnalyzing: {file}...", file=sys.stderr)

        try:
            r = analyze_track(file, sr=args.sr)
            results.append(r)

            if args.json:
                continue

            print(r)

            if args.debug:
                print("\n  Profile votes:")
                for profile, key in r.profile_votes.items():
                    print(f"    {profile:<25} → {key}")
                if r.frame_votes:
                    from collections import Counter
                    count = Counter(r.frame_votes)
                    print(f"\n  Frame votes ({len(r.frame_votes)} segments):")
                    for key, n in count.most_common(5):
                        bar = "█" * n
                        print(f"    {key:<14} {bar} ({n})")

            if args.suggestions:
                suggestions = suggest_next(r.key)
                print(f"\n  Compatible keys for transition from {r.key} ({r.camelot}):")
                for s in suggestions:
                    print(f"    {s['camelot']:<5} {s['key']:<14} — {s['description']} [{s['level']}]")

        except Exception as e:
            print(f"Error analyzing {file}: {e}", file=sys.stderr)

    # Compatibility between two tracks
    if args.compatible_with and results:
        print(f"\nAnalyzing: {args.compatible_with}...", file=sys.stderr)
        try:
            r_b = analyze_track(args.compatible_with, sr=args.sr)
            if not args.json:
                print(r_b)

            r_a = results[0]

            compat = compatibility(r_a.key_end, r_b.key_start)

            if args.json:
                results.append(r_b)
            else:
                print(f"\n{'─' * 56}")
                print("  TRANSITION COMPATIBILITY")
                print(f"{'─' * 56}")
                print(f"  {r_a.file}")
                print(f"    End key:   {r_a.key_end} ({r_a.camelot_end})")
                print(f"  {r_b.file}")
                print(f"    Start key: {r_b.key_start} ({r_b.camelot_start})")
                print(f"{'─' * 56}")
                emoji = {"perfect": "✓", "good": "~", "risky": "!", "incompatible": "✗"}
                e = emoji.get(compat["level"], "?")
                print(f"  [{e}] {compat['level'].upper()} — {compat['description']}")
                print(f"  Camelot distance: {compat['distance']}")
                print(f"{'─' * 56}")

        except Exception as e:
            print(f"Error analyzing {args.compatible_with}: {e}", file=sys.stderr)

    # JSON output
    if args.json:
        data = [r.to_dict() for r in results]
        print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
