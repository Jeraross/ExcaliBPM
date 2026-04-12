"""
Integration tests for Spotify download functionality.

These tests require:
  - spotdl installed (pip install spotdl)
  - ffmpeg available
  - Internet access

All tests are marked @pytest.mark.slow and skipped when spotdl is unavailable.
Run with: pytest tests/test_spotify_integration.py -v
"""

import os
import time
import tempfile
from pathlib import Path

import pytest

from tests.conftest import spotdl_available

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not spotdl_available, reason="spotdl not installed"),
]

# A short, freely-available Spotify track for testing
# (30-second preview should still work for analysis)
_TEST_TRACK_URL = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
_TEST_INVALID_URL = "https://open.spotify.com/track/0000000000000000000000"


class TestSingleTrackDownload:
    def test_download_creates_file(self, tmp_path):
        from excalibpm.spotify import SpotifyConfig, SpotifySession

        config = SpotifyConfig()
        with SpotifySession(config) as session:
            session._get_output_dir = lambda: str(tmp_path)  # override to tmp_path
            tracks = session.download(_TEST_TRACK_URL)

        assert len(tracks) >= 1
        assert tracks[0].success
        assert Path(tracks[0].local_path).exists()
        assert Path(tracks[0].local_path).stat().st_size > 0

    def test_downloaded_file_is_audio(self, tmp_path):
        """librosa should be able to load the downloaded file."""
        import librosa
        from excalibpm.spotify import SpotifyConfig, SpotifySession

        config = SpotifyConfig()
        local_path = None
        with SpotifySession(config) as session:
            tracks = session.download(_TEST_TRACK_URL)
            assert tracks, "No tracks downloaded"
            local_path = tracks[0].local_path
            # Load inside the context so file still exists
            y, sr = librosa.load(local_path, sr=22050, duration=5.0)
            assert len(y) > 0

    def test_temp_cleanup_after_exit(self):
        from excalibpm.spotify import SpotifyConfig, SpotifySession

        config = SpotifyConfig()  # temp mode
        saved_path = None
        with SpotifySession(config) as session:
            tracks = session.download(_TEST_TRACK_URL)
            if tracks and tracks[0].success:
                saved_path = tracks[0].local_path

        if saved_path:
            assert not Path(saved_path).exists(), (
                f"Temp file not cleaned up: {saved_path}"
            )


class TestCacheMode:
    def test_cache_hit_on_second_download(self, tmp_path):
        from excalibpm.spotify import SpotifyConfig, SpotifySession

        cache_dir = str(tmp_path / "cache")
        config = SpotifyConfig(cache_dir=cache_dir)

        # First download
        with SpotifySession(config) as session:
            tracks1 = session.download(_TEST_TRACK_URL)
        assert tracks1 and tracks1[0].success
        path1 = tracks1[0].local_path

        # Second download — should be a cache hit (no new download)
        with SpotifySession(config) as session:
            tracks2 = session.download(_TEST_TRACK_URL)
        assert tracks2 and tracks2[0].success
        path2 = tracks2[0].local_path

        # Same file path
        assert path1 == path2
        assert Path(path2).exists()


class TestTimeoutHandling:
    def test_very_short_timeout_raises(self, tmp_path):
        from excalibpm.spotify import SpotifyConfig, SpotifySession, DownloadError

        config = SpotifyConfig(timeout=1)  # 1 second — unreasonably short
        with SpotifySession(config) as session:
            with pytest.raises(DownloadError, match="timed out"):
                session.download(_TEST_TRACK_URL)


class TestInvalidUrlHandling:
    def test_invalid_url_raises(self, tmp_path):
        from excalibpm.spotify import (
            SpotifyConfig, SpotifySession,
            InvalidSpotifyUrlError, DownloadError,
        )

        config = SpotifyConfig()
        with SpotifySession(config) as session:
            with pytest.raises((InvalidSpotifyUrlError, DownloadError)):
                session.download("https://open.spotify.com/track/tooshort")
