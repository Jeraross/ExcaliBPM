"""
Spotify integration for ExcaliBPM.

Downloads audio from Spotify URLs using spotDL CLI and provides
a clean interface for analysis. spotdl is an OPTIONAL dependency —
core analysis works without it.

Design constraints:
- spotdl has no stable Python API — subprocess ONLY.
- Never download without cleanup guarantee — always use SpotifySession.
- All Spotify functionality is optional; core analysis never imports this module.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


# ── Custom Exceptions ─────────────────────────────────────────────────────────

class SpotifyError(Exception):
    """Base exception for Spotify integration errors."""


class SpotdlNotFoundError(SpotifyError):
    """Raised when spotdl CLI is not installed."""
    def __init__(self):
        super().__init__(
            "spotdl not found. Install it with:\n"
            "  pip install spotdl\n"
            "On Windows, you may also need:\n"
            "  pip install spotdl[ffmpeg]\n"
            "Verify with: spotdl --version"
        )


class FFmpegNotFoundError(SpotifyError):
    """Raised when ffmpeg is not installed."""
    def __init__(self):
        super().__init__(
            "ffmpeg not found. Install it:\n"
            "  Ubuntu/Debian:  sudo apt install ffmpeg\n"
            "  macOS:          brew install ffmpeg\n"
            "  Windows:        choco install ffmpeg\n"
            "                  or: https://ffmpeg.org/download.html\n"
            "Verify with: ffmpeg -version"
        )


class DownloadError(SpotifyError):
    """Raised when a spotdl download fails."""


class InvalidSpotifyUrlError(SpotifyError):
    """Raised when a Spotify URL cannot be parsed."""


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class SpotifyConfig:
    """Configuration for Spotify download behavior."""
    cache_dir: Optional[str] = None
    cache_max_mb: int = 500
    format: str = "mp3"
    threads: int = 4
    timeout: int = 120
    keep_files: bool = False
    output_dir: str = "./downloads"
    filename_template: str = "{artist} - {title}"


@dataclass
class SpotifyTrackInfo:
    """Information about a downloaded Spotify track."""
    url: str
    type: str          # "track" | "album" | "playlist"
    spotify_id: str
    local_path: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    error: str = ""

    @property
    def success(self) -> bool:
        """True when the track was successfully downloaded."""
        return bool(self.local_path) and not self.error


# ── URL Parsing ───────────────────────────────────────────────────────────────

# Handles all Spotify URL variants:
#   https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC
#   http://open.spotify.com/album/ID
#   open.spotify.com/playlist/ID  (no scheme)
#   https://open.spotify.com/intl-pt-BR/track/ID  (locale prefix)
#   https://open.spotify.com/intl-xx/track/ID?si=abc123  (with query params)
_SPOTIFY_URL_RE = re.compile(
    r"^(?:https?://)?open\.spotify\.com"
    r"(?:/intl-[a-z]{2}(?:-[A-Z]{2})?)?"
    r"/(track|album|playlist)"
    r"/([A-Za-z0-9]{22})"
    r"(?:[?#].*)?"
    r"$",
    re.IGNORECASE,
)


def classify_url(url: str) -> Optional[tuple]:
    """
    Parse a Spotify URL and return (type, spotify_id) or None if invalid.

    Handles all URL variants including locale prefixes and query params.
    """
    url = url.strip()
    m = _SPOTIFY_URL_RE.match(url)
    if m:
        return m.group(1).lower(), m.group(2)
    return None


def is_spotify_url(input_str: str) -> bool:
    """Return True if input looks like a valid Spotify URL."""
    return classify_url(input_str) is not None


def _url_hash(url: str) -> str:
    """Generate a deterministic, fixed-length (16-char) hash of a URL."""
    return hashlib.sha256(url.strip().encode()).hexdigest()[:16]


# ── Cache Manager ─────────────────────────────────────────────────────────────

class CacheManager:
    """
    LRU cache for downloaded Spotify tracks.

    Persists index in .cache_index.json within the cache directory.
    Handles index corruption gracefully by recreating it empty.
    """

    INDEX_FILENAME = ".cache_index.json"

    def __init__(self, cache_dir: str, max_mb: int = 500):
        self.cache_dir = Path(cache_dir)
        self.max_bytes = max_mb * 1024 * 1024
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict = self._load_index()

    def _index_path(self) -> Path:
        return self.cache_dir / self.INDEX_FILENAME

    def _load_index(self) -> dict:
        index_path = self._index_path()
        if index_path.exists():
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except (json.JSONDecodeError, OSError, ValueError):
                pass
        return {}

    def _save_index(self) -> None:
        try:
            with open(self._index_path(), "w", encoding="utf-8") as f:
                json.dump(self._index, f, indent=2)
        except OSError:
            pass  # Best-effort

    def get(self, url: str) -> Optional[str]:
        """Return cached file path for URL, or None on cache miss."""
        key = _url_hash(url)
        entry = self._index.get(key)
        if entry is None:
            return None
        path = Path(entry["path"])
        if not path.exists():
            # File deleted externally — remove stale entry
            del self._index[key]
            self._save_index()
            return None
        # Update last-access timestamp
        entry["last_access"] = time.time()
        self._save_index()
        return str(path)

    def register(self, url: str, file_path: str) -> None:
        """Register a downloaded file in the cache."""
        path = Path(file_path)
        if not path.exists():
            return
        try:
            size = path.stat().st_size
        except OSError:
            return
        key = _url_hash(url)
        self._index[key] = {
            "url": url,
            "path": str(path),
            "size_bytes": size,
            "last_access": time.time(),
        }
        self._save_index()
        self._evict_if_needed()

    def _total_size(self) -> int:
        return sum(e.get("size_bytes", 0) for e in self._index.values())

    def _evict_if_needed(self) -> None:
        """Evict least-recently-accessed entries until under size limit."""
        while self._total_size() > self.max_bytes and self._index:
            lru_key = min(
                self._index,
                key=lambda k: self._index[k].get("last_access", 0),
            )
            entry = self._index.pop(lru_key)
            try:
                p = Path(entry["path"])
                if p.exists():
                    p.unlink()
            except OSError:
                pass
        self._save_index()

    def clear(self) -> int:
        """Delete all cached files and reset index. Returns number of files deleted."""
        deleted = 0
        for entry in self._index.values():
            try:
                p = Path(entry["path"])
                if p.exists():
                    p.unlink()
                    deleted += 1
            except OSError:
                pass
        self._index = {}
        self._save_index()
        return deleted

    def stats(self) -> dict:
        """Return cache statistics."""
        total_bytes = self._total_size()
        return {
            "entries": len(self._index),
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "max_mb": self.max_bytes // (1024 * 1024),
            "cache_dir": str(self.cache_dir),
        }


# ── Dependency Checking ───────────────────────────────────────────────────────

_deps_cache: Optional[dict] = None


def check_dependencies() -> dict:
    """
    Verify spotdl and ffmpeg are available via subprocess.

    Results are cached after the first call (checked once per session).
    Returns dict with bool values: {"spotdl": bool, "ffmpeg": bool}.
    """
    global _deps_cache
    if _deps_cache is not None:
        return _deps_cache

    result: dict = {}
    checks = [
        ("spotdl", ["spotdl", "--version"]),
        ("ffmpeg", ["ffmpeg", "-version"]),
    ]
    for tool, cmd in checks:
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=10)
            result[tool] = r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            result[tool] = False

    _deps_cache = result
    return result


def _require_dependencies() -> None:
    """Raise appropriate exception if required dependencies are missing."""
    deps = check_dependencies()
    if not deps.get("spotdl"):
        raise SpotdlNotFoundError()
    if not deps.get("ffmpeg"):
        raise FFmpegNotFoundError()


# ── Download Engine ───────────────────────────────────────────────────────────

def _parse_filename(filename: str) -> tuple:
    """
    Parse artist and title from 'Artist - Title.ext' filename pattern.
    Returns (artist, title).
    """
    stem = Path(filename).stem
    if " - " in stem:
        artist, title = stem.split(" - ", 1)
        return artist.strip(), title.strip()
    return "", stem.strip()


def download_spotify(
    url: str,
    output_dir: str,
    config: Optional[SpotifyConfig] = None,
) -> list:
    """
    Download audio from a Spotify URL to output_dir using spotdl CLI.

    Returns a list of SpotifyTrackInfo objects (one per track downloaded).
    Raises SpotdlNotFoundError, FFmpegNotFoundError, DownloadError, or
    InvalidSpotifyUrlError on failure.
    """
    if config is None:
        config = SpotifyConfig()

    parsed = classify_url(url)
    if parsed is None:
        raise InvalidSpotifyUrlError(f"Cannot parse Spotify URL: {url!r}")

    url_type, spotify_id = parsed
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Snapshot files before download to detect new ones
    before = set(out_path.glob(f"*.{config.format}"))

    cmd = [
        "spotdl",
        "download",
        url,
        "--output", str(out_path),
        "--format", config.format,
        "--threads", str(config.threads),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.timeout,
        )
    except subprocess.TimeoutExpired:
        raise DownloadError(
            f"Download timed out after {config.timeout}s for URL: {url}"
        )
    except FileNotFoundError:
        raise SpotdlNotFoundError()

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise DownloadError(
            f"spotdl exited with code {proc.returncode}: {stderr[:500]}"
        )

    # Find newly created files
    after = set(out_path.glob(f"*.{config.format}"))
    new_files = sorted(after - before)

    if not new_files:
        # spotdl sometimes exits 0 when file already existed; return all files
        new_files = sorted(after)

    tracks = []
    for f in new_files:
        artist, title = _parse_filename(f.name)
        tracks.append(SpotifyTrackInfo(
            url=url,
            type=url_type,
            spotify_id=spotify_id,
            local_path=str(f),
            title=title,
            artist=artist,
        ))

    return tracks


# ── SpotifySession Context Manager ────────────────────────────────────────────

class SpotifySession:
    """
    Context manager that guarantees cleanup of downloaded audio files.

    Three operating modes:
    - Temp mode (default):
        Downloads to a tmpdir, deletes on __exit__. Zero disk footprint.
    - Cache mode (cache_dir set):
        Checks cache first. Downloads on miss. Persists files with LRU eviction.
        Only individual tracks are cached (not full playlists/albums).
    - Keep mode (keep_files=True):
        Downloads to output_dir, never deletes. For building a local library.

    Usage:
        with SpotifySession(config) as session:
            tracks = session.download("https://open.spotify.com/track/...")
            for t in tracks:
                result = analyze_track(t.local_path)
    """

    def __init__(self, config: Optional[SpotifyConfig] = None):
        self.config = config or SpotifyConfig()
        self._temp_dir: Optional[str] = None
        self._cache: Optional[CacheManager] = None
        self._deps_ok: bool = False

    def __enter__(self) -> "SpotifySession":
        self._ensure_deps()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._cleanup()
        return False  # Do not suppress exceptions

    def _ensure_deps(self) -> None:
        if not self._deps_ok:
            _require_dependencies()
            self._deps_ok = True

    def _get_cache(self) -> Optional[CacheManager]:
        if self.config.cache_dir is not None:
            if self._cache is None:
                self._cache = CacheManager(
                    self.config.cache_dir,
                    max_mb=self.config.cache_max_mb,
                )
            return self._cache
        return None

    def _get_output_dir(self) -> str:
        """Return the directory to download into based on the operating mode."""
        if self.config.keep_files:
            path = Path(self.config.output_dir)
            path.mkdir(parents=True, exist_ok=True)
            return str(path)
        elif self.config.cache_dir is not None:
            return self.config.cache_dir
        else:
            # Temp mode: create on first use
            if self._temp_dir is None:
                self._temp_dir = tempfile.mkdtemp(prefix="excalibpm_")
            return self._temp_dir

    def download(
        self,
        url: str,
        on_progress: Optional[Callable] = None,
    ) -> list:
        """
        Download audio for the given Spotify URL.

        Checks cache first (if in cache mode). Returns list of SpotifyTrackInfo.
        For playlists/albums, returns one entry per track.
        """
        self._ensure_deps()

        parsed = classify_url(url)
        if parsed is None:
            raise InvalidSpotifyUrlError(f"Cannot parse Spotify URL: {url!r}")

        url_type, spotify_id = parsed
        cache = self._get_cache()

        # Cache check — only for single tracks
        if cache is not None and url_type == "track":
            cached_path = cache.get(url)
            if cached_path:
                artist, title = _parse_filename(Path(cached_path).name)
                if on_progress:
                    on_progress(f"Cache hit: {cached_path}", 1, 1)
                return [SpotifyTrackInfo(
                    url=url,
                    type=url_type,
                    spotify_id=spotify_id,
                    local_path=cached_path,
                    title=title,
                    artist=artist,
                )]

        output_dir = self._get_output_dir()

        if on_progress:
            on_progress(f"Downloading {url_type}: {url}", 0, 1)

        tracks = download_spotify(url, output_dir, self.config)

        # Register individual tracks in cache (not bulk playlist downloads)
        if cache is not None and url_type == "track":
            for t in tracks:
                if t.local_path:
                    cache.register(url, t.local_path)

        if on_progress:
            on_progress(f"Downloaded {len(tracks)} track(s)", 1, 1)

        return tracks

    def _cleanup(self) -> None:
        """Remove temp directory if in temp mode."""
        if not self.config.keep_files and self.config.cache_dir is None:
            if self._temp_dir is not None:
                try:
                    shutil.rmtree(self._temp_dir, ignore_errors=True)
                except OSError:
                    pass
                self._temp_dir = None

    def cache_info(self) -> Optional[dict]:
        """Return cache statistics, or None if not in cache mode."""
        cache = self._get_cache()
        return cache.stats() if cache else None

    def cache_clear(self) -> int:
        """Clear the cache. Returns number of files deleted."""
        cache = self._get_cache()
        return cache.clear() if cache else 0
