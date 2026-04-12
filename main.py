#!/usr/bin/env python3
"""
CLI for music analysis.

Usage:
    python main.py track.wav
    python main.py track1.mp3 track2.flac --json
    python main.py track_a.wav --compatible-with track_b.wav
    python main.py https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC
    python main.py https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M --cache-dir /tmp/cache
    python main.py --check-deps
"""

import argparse
import json
import sys
import os

from excalibpm import (
    analyze_track,
    analyze,
    compatibility,
    suggest_next,
    is_spotify_url,
    SpotifyConfig,
)


def _progress(message: str, current: int, total: int) -> None:
    print(f"  [{current}/{total}] {message}", file=sys.stderr)


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

  # Spotify (requires spotdl + ffmpeg)
  python main.py https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC
  python main.py https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M --cache-dir /tmp/cache
  python main.py track_a.wav --compatible-with https://open.spotify.com/track/...
  python main.py --check-deps
        """,
    )

    parser.add_argument(
        "files",
        nargs="*",
        help="Audio file(s) or Spotify URL(s) to analyze",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--compatible-with",
        metavar="FILE_OR_URL",
        help="Check harmonic compatibility with another file or Spotify URL",
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

    # ── Spotify options ───────────────────────────────────────────────────────
    spotify_group = parser.add_argument_group("Spotify options")
    spotify_group.add_argument(
        "--cache-dir",
        metavar="DIR",
        default=None,
        help="Enable cache mode: persist downloaded files in DIR",
    )
    spotify_group.add_argument(
        "--cache-max-mb",
        type=int,
        default=500,
        metavar="N",
        help="Cache size limit in MB (default: 500)",
    )
    spotify_group.add_argument(
        "--keep-downloads",
        action="store_true",
        help="Keep downloaded files instead of deleting after analysis",
    )
    spotify_group.add_argument(
        "--output-dir",
        metavar="DIR",
        default="./downloads",
        help="Directory for kept/downloaded files (default: ./downloads)",
    )
    spotify_group.add_argument(
        "--format",
        choices=["mp3", "m4a", "opus", "flac"],
        default="mp3",
        help="Audio format for Spotify downloads (default: mp3)",
    )
    spotify_group.add_argument(
        "--check-deps",
        action="store_true",
        help="Verify spotdl and ffmpeg installation and exit",
    )
    spotify_group.add_argument(
        "--cache-info",
        action="store_true",
        help="Show cache statistics and exit",
    )
    spotify_group.add_argument(
        "--cache-clear",
        action="store_true",
        help="Wipe cache and exit",
    )

    args = parser.parse_args()

    # ── --check-deps ──────────────────────────────────────────────────────────
    if args.check_deps:
        from excalibpm import check_dependencies
        deps = check_dependencies()
        for tool, ok in deps.items():
            status = "OK" if ok else "NOT FOUND"
            print(f"  {tool:<10} {status}")
        if not all(deps.values()):
            print(
                "\nTo install missing dependencies:\n"
                "  pip install spotdl\n"
                "  # ffmpeg: see https://ffmpeg.org/download.html",
                file=sys.stderr,
            )
            sys.exit(1)
        sys.exit(0)

    # ── Build SpotifyConfig ───────────────────────────────────────────────────
    spotify_config = SpotifyConfig(
        cache_dir=args.cache_dir,
        cache_max_mb=args.cache_max_mb,
        format=args.format,
        keep_files=args.keep_downloads,
        output_dir=args.output_dir,
    )

    # ── --cache-info / --cache-clear ──────────────────────────────────────────
    if args.cache_info or args.cache_clear:
        if not args.cache_dir:
            print("Error: --cache-info and --cache-clear require --cache-dir", file=sys.stderr)
            sys.exit(1)
        from excalibpm import SpotifySession
        with SpotifySession.__new__(SpotifySession) as session:
            session.config = spotify_config
            session._temp_dir = None
            session._cache = None
            session._deps_ok = True  # skip dep check for cache ops
            if args.cache_info:
                info = session.cache_info()
                print(json.dumps(info, indent=2))
            if args.cache_clear:
                n = session.cache_clear()
                print(f"Cleared {n} cached file(s).")
        sys.exit(0)

    if not args.files and not args.compatible_with:
        parser.print_help()
        sys.exit(1)

    # ── Check deps early if any Spotify URL is present ────────────────────────
    inputs = list(args.files or [])
    if args.compatible_with:
        inputs_for_check = inputs + [args.compatible_with]
    else:
        inputs_for_check = inputs

    has_spotify = any(is_spotify_url(i) for i in inputs_for_check)
    if has_spotify:
        from excalibpm import check_dependencies
        deps = check_dependencies()
        if not deps.get("spotdl"):
            print(
                "Error: spotdl is required for Spotify URLs.\n"
                "Install with: pip install spotdl",
                file=sys.stderr,
            )
            sys.exit(1)
        if not deps.get("ffmpeg"):
            print(
                "Error: ffmpeg is required for Spotify downloads.\n"
                "Install: sudo apt install ffmpeg  (Linux)\n"
                "         brew install ffmpeg       (macOS)\n"
                "         choco install ffmpeg      (Windows)",
                file=sys.stderr,
            )
            sys.exit(1)

    results = []

    for input_item in (args.files or []):
        if not is_spotify_url(input_item) and not os.path.exists(input_item):
            print(f"File not found: {input_item}", file=sys.stderr)
            continue

        print(f"\nAnalyzing: {input_item}...", file=sys.stderr)

        try:
            r = analyze(input_item, spotify_config=spotify_config, on_progress=_progress)

            if isinstance(r, list):
                results.extend(r)
                if not args.json:
                    for item in r:
                        print(item)
                        _print_extras(item, args)
            else:
                results.append(r)
                if not args.json:
                    print(r)
                    _print_extras(r, args)

        except Exception as e:
            print(f"Error analyzing {input_item}: {e}", file=sys.stderr)

    # ── Compatibility between two tracks ──────────────────────────────────────
    if args.compatible_with and results:
        target = args.compatible_with
        if not is_spotify_url(target) and not os.path.exists(target):
            print(f"File not found: {target}", file=sys.stderr)
        else:
            print(f"\nAnalyzing: {target}...", file=sys.stderr)
            try:
                r_b_raw = analyze(target, spotify_config=spotify_config, on_progress=_progress)
                r_b = r_b_raw[0] if isinstance(r_b_raw, list) else r_b_raw

                if not args.json:
                    print(r_b)

                r_a = results[0]
                compat = compatibility(r_a.key_end, r_b.key_start)

                if args.json:
                    if isinstance(r_b_raw, list):
                        results.extend(r_b_raw)
                    else:
                        results.append(r_b)
                else:
                    print(f"\n{'─' * 56}")
                    print("  TRANSITION COMPATIBILITY")
                    print(f"{'─' * 56}")
                    print(f"  {r_a.file or r_a.spotify_url}")
                    print(f"    End key:   {r_a.key_end} ({r_a.camelot_end})")
                    print(f"  {r_b.file or r_b.spotify_url}")
                    print(f"    Start key: {r_b.key_start} ({r_b.camelot_start})")
                    print(f"{'─' * 56}")
                    emoji = {"perfect": "✓", "good": "~", "risky": "!", "incompatible": "✗"}
                    e = emoji.get(compat["level"], "?")
                    print(f"  [{e}] {compat['level'].upper()} — {compat['description']}")
                    print(f"  Camelot distance: {compat['distance']}")
                    print(f"{'─' * 56}")

            except Exception as e:
                print(f"Error analyzing {target}: {e}", file=sys.stderr)

    # ── JSON output ───────────────────────────────────────────────────────────
    if args.json:
        data = [r.to_dict() for r in results]
        print(json.dumps(data, indent=2, ensure_ascii=False))


def _print_extras(r, args) -> None:
    """Print debug votes and key suggestions if requested."""
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


if __name__ == "__main__":
    main()
