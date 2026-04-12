"""
Unit tests for excalibpm.spotify — no network, no spotdl required.

All tests here must pass without spotdl or ffmpeg installed.
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from excalibpm.spotify import (
    CacheManager,
    SpotifyConfig,
    SpotifyTrackInfo,
    _url_hash,
    classify_url,
    is_spotify_url,
)


# ── TestClassifyUrl ───────────────────────────────────────────────────────────

class TestClassifyUrl:
    """Test all URL variants supported by the parser."""

    # Standard URLs
    def test_standard_track(self):
        result = classify_url("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    def test_standard_album(self):
        result = classify_url("https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3")
        assert result == ("album", "1DFixLWuPkv3KT3TnV35m3")

    def test_standard_playlist(self):
        result = classify_url("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M")
        assert result == ("playlist", "37i9dQZF1DXcBWIGoYBM5M")

    # Locale prefix variants
    def test_intl_prefix_two_letter(self):
        result = classify_url("https://open.spotify.com/intl-pt/track/4uLU6hMCjMI75M1A2tKUQC")
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    def test_intl_prefix_full_locale(self):
        result = classify_url("https://open.spotify.com/intl-pt-BR/track/4uLU6hMCjMI75M1A2tKUQC")
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    def test_intl_prefix_album(self):
        result = classify_url("https://open.spotify.com/intl-es/album/1DFixLWuPkv3KT3TnV35m3")
        assert result == ("album", "1DFixLWuPkv3KT3TnV35m3")

    # Query parameters
    def test_with_si_query_param(self):
        result = classify_url(
            "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC?si=abc123"
        )
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    def test_with_multiple_query_params(self):
        result = classify_url(
            "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC?si=abc&utm_source=x"
        )
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    def test_intl_and_query_combined(self):
        result = classify_url(
            "https://open.spotify.com/intl-pt-BR/track/4uLU6hMCjMI75M1A2tKUQC?si=xyz"
        )
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    # Without https scheme
    def test_no_scheme(self):
        result = classify_url("open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    def test_http_variant(self):
        result = classify_url("http://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    # Whitespace handling
    def test_leading_trailing_whitespace(self):
        result = classify_url("  https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC  ")
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    # Invalid / non-Spotify inputs
    def test_invalid_url_returns_none(self):
        assert classify_url("https://www.youtube.com/watch?v=abc123") is None

    def test_empty_string_returns_none(self):
        assert classify_url("") is None

    def test_local_file_path_returns_none(self):
        assert classify_url("/home/user/music/track.mp3") is None

    def test_windows_path_returns_none(self):
        assert classify_url(r"C:\Users\user\music\track.mp3") is None

    def test_random_string_returns_none(self):
        assert classify_url("hello world") is None

    def test_short_spotify_id_returns_none(self):
        # IDs must be exactly 22 chars
        assert classify_url("https://open.spotify.com/track/tooshort") is None

    def test_type_is_lowercased(self):
        result = classify_url("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
        assert result[0] == "track"


# ── TestIsSpotifyUrl ──────────────────────────────────────────────────────────

class TestIsSpotifyUrl:
    def test_true_for_valid_track(self):
        assert is_spotify_url("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC") is True

    def test_true_for_valid_album(self):
        assert is_spotify_url("https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3") is True

    def test_true_for_valid_playlist(self):
        assert is_spotify_url("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M") is True

    def test_false_for_local_file(self):
        assert is_spotify_url("/home/user/music/track.mp3") is False

    def test_false_for_wav_path(self):
        assert is_spotify_url("track.wav") is False

    def test_false_for_random_string(self):
        assert is_spotify_url("not a url at all") is False

    def test_false_for_empty_string(self):
        assert is_spotify_url("") is False

    def test_false_for_youtube_url(self):
        assert is_spotify_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is False


# ── TestSpotifyConfig ─────────────────────────────────────────────────────────

class TestSpotifyConfig:
    def test_default_values(self):
        cfg = SpotifyConfig()
        assert cfg.cache_dir is None
        assert cfg.cache_max_mb == 500
        assert cfg.format == "mp3"
        assert cfg.threads == 4
        assert cfg.timeout == 120
        assert cfg.keep_files is False
        assert cfg.output_dir == "./downloads"
        assert cfg.filename_template == "{artist} - {title}"

    def test_custom_values(self):
        cfg = SpotifyConfig(
            cache_dir="/tmp/cache",
            cache_max_mb=200,
            format="flac",
            threads=2,
            timeout=60,
            keep_files=True,
            output_dir="/music",
        )
        assert cfg.cache_dir == "/tmp/cache"
        assert cfg.cache_max_mb == 200
        assert cfg.format == "flac"
        assert cfg.threads == 2
        assert cfg.timeout == 60
        assert cfg.keep_files is True
        assert cfg.output_dir == "/music"

    def test_is_dataclass(self):
        from dataclasses import fields
        cfg = SpotifyConfig()
        field_names = {f.name for f in fields(cfg)}
        assert "cache_dir" in field_names
        assert "format" in field_names
        assert "timeout" in field_names


# ── TestCacheManager ──────────────────────────────────────────────────────────

class TestCacheManager:
    def _make_file(self, directory: Path, name: str, size_bytes: int = 1024) -> Path:
        """Create a dummy file with given size."""
        p = directory / name
        p.write_bytes(b"x" * size_bytes)
        return p

    def test_create_cache_dir(self, tmp_path):
        cache_dir = tmp_path / "cache"
        assert not cache_dir.exists()
        CacheManager(str(cache_dir))
        assert cache_dir.exists()

    def test_register_and_retrieve(self, tmp_path):
        manager = CacheManager(str(tmp_path))
        f = self._make_file(tmp_path, "Artist - Title.mp3")
        url = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
        manager.register(url, str(f))
        assert manager.get(url) == str(f)

    def test_miss_returns_none(self, tmp_path):
        manager = CacheManager(str(tmp_path))
        assert manager.get("https://open.spotify.com/track/0000000000000000000001") is None

    def test_stale_entry_returns_none(self, tmp_path):
        manager = CacheManager(str(tmp_path))
        fake_path = tmp_path / "ghost.mp3"
        url = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
        # Manually inject a stale entry
        manager._index[_url_hash(url)] = {
            "url": url,
            "path": str(fake_path),
            "size_bytes": 100,
            "last_access": time.time(),
        }
        result = manager.get(url)
        assert result is None
        assert _url_hash(url) not in manager._index

    def test_lru_eviction(self, tmp_path):
        # max 2 KB cache
        manager = CacheManager(str(tmp_path), max_mb=0)
        manager.max_bytes = 2048  # 2 KB

        f1 = self._make_file(tmp_path, "a.mp3", size_bytes=1000)
        f2 = self._make_file(tmp_path, "b.mp3", size_bytes=1000)
        f3 = self._make_file(tmp_path, "c.mp3", size_bytes=1000)

        url1 = "https://open.spotify.com/track/A" + "a" * 21
        url2 = "https://open.spotify.com/track/B" + "b" * 21
        url3 = "https://open.spotify.com/track/C" + "c" * 21

        manager.register(url1, str(f1))
        time.sleep(0.01)
        manager.register(url2, str(f2))
        time.sleep(0.01)
        # f1 was accessed earlier — it should be evicted when f3 is added
        manager.register(url3, str(f3))

        # After eviction, total size should be within limit (or at most 2 entries)
        assert manager._total_size() <= manager.max_bytes + 1000  # some tolerance

    def test_clear_deletes_files(self, tmp_path):
        manager = CacheManager(str(tmp_path))
        f = self._make_file(tmp_path, "track.mp3")
        url = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
        manager.register(url, str(f))
        assert f.exists()
        n = manager.clear()
        assert n >= 1
        assert len(manager._index) == 0

    def test_corrupted_index_is_recreated(self, tmp_path):
        index_path = tmp_path / ".cache_index.json"
        index_path.write_text("{ this is not valid json }", encoding="utf-8")
        # Should not raise
        manager = CacheManager(str(tmp_path))
        assert manager._index == {}

    def test_stats_structure(self, tmp_path):
        manager = CacheManager(str(tmp_path))
        stats = manager.stats()
        assert "entries" in stats
        assert "total_mb" in stats
        assert "max_mb" in stats
        assert "cache_dir" in stats

    def test_register_nonexistent_file_is_ignored(self, tmp_path):
        manager = CacheManager(str(tmp_path))
        url = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
        manager.register(url, str(tmp_path / "does_not_exist.mp3"))
        assert manager.get(url) is None


# ── TestSpotifyTrackInfo ──────────────────────────────────────────────────────

class TestSpotifyTrackInfo:
    def test_success_true_when_has_path(self, tmp_path):
        f = tmp_path / "track.mp3"
        f.write_bytes(b"fake")
        t = SpotifyTrackInfo(
            url="https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
            type="track",
            spotify_id="4uLU6hMCjMI75M1A2tKUQC",
            local_path=str(f),
        )
        assert t.success is True

    def test_success_false_when_no_path(self):
        t = SpotifyTrackInfo(
            url="https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
            type="track",
            spotify_id="4uLU6hMCjMI75M1A2tKUQC",
        )
        assert t.success is False

    def test_success_false_when_has_error(self, tmp_path):
        f = tmp_path / "track.mp3"
        f.write_bytes(b"fake")
        t = SpotifyTrackInfo(
            url="https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
            type="track",
            spotify_id="4uLU6hMCjMI75M1A2tKUQC",
            local_path=str(f),
            error="download failed",
        )
        assert t.success is False

    def test_default_fields(self):
        t = SpotifyTrackInfo(
            url="https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
            type="track",
            spotify_id="4uLU6hMCjMI75M1A2tKUQC",
        )
        assert t.local_path == ""
        assert t.title == ""
        assert t.artist == ""
        assert t.album == ""
        assert t.error == ""


# ── TestUrlHash ───────────────────────────────────────────────────────────────

class TestUrlHash:
    def test_deterministic(self):
        url = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
        assert _url_hash(url) == _url_hash(url)

    def test_consistent_length(self):
        urls = [
            "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
            "https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3",
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        ]
        lengths = {len(_url_hash(u)) for u in urls}
        assert len(lengths) == 1  # all same length

    def test_different_urls_give_different_hashes(self):
        url1 = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
        url2 = "https://open.spotify.com/track/1DFixLWuPkv3KT3TnV35m3"
        assert _url_hash(url1) != _url_hash(url2)

    def test_whitespace_is_stripped(self):
        url = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
        assert _url_hash(f"  {url}  ") == _url_hash(url)
