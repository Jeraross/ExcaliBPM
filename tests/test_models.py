"""
Tests for music_analyzer.models — MusicAnalysis dataclass.
"""

from excalibpm.models import MusicAnalysis


class TestMusicAnalysisStr:
    def test_str_contains_filename(self, sample_analysis):
        assert "track.wav" in str(sample_analysis)

    def test_str_contains_bpm(self, sample_analysis):
        assert "128" in str(sample_analysis)

    def test_str_contains_overall_key(self, sample_analysis):
        assert "C Major" in str(sample_analysis)

    def test_str_contains_camelot_codes(self, sample_analysis):
        assert "8B" in str(sample_analysis)   # C Major → 8B

    def test_str_without_file_omits_empty_lines(self):
        analysis = MusicAnalysis(
            key="A Minor",
            key_confidence=0.9,
            key_start="A Minor",
            start_confidence=0.8,
            key_end="A Minor",
            end_confidence=0.8,
            bpm=120.0,
            duration_seconds=60.0,
            file="",
        )
        for line in str(analysis).splitlines():
            assert line.strip() != ""

    def test_str_duration_formatted_as_minutes_seconds(self, sample_analysis):
        # 212.5 s = 3 min 32 s
        assert "3:32" in str(sample_analysis)


class TestMusicAnalysisToDict:
    def test_required_keys_present(self, sample_analysis):
        d = sample_analysis.to_dict()
        expected = {
            "file", "duration_seconds", "bpm",
            "key", "camelot", "openkey", "key_confidence",
            "key_start", "camelot_start", "start_confidence",
            "key_end", "camelot_end", "end_confidence",
        }
        assert expected.issubset(d.keys())

    def test_bpm_value_correct(self, sample_analysis):
        assert sample_analysis.to_dict()["bpm"] == 128.0

    def test_camelot_codes_correct(self, sample_analysis):
        d = sample_analysis.to_dict()
        assert d["camelot"] == "8B"      # C Major
        assert d["camelot_end"] == "9B"  # G Major

    def test_openkey_correct(self, sample_analysis):
        assert sample_analysis.to_dict()["openkey"] == "1d"  # C Major

    def test_confidence_rounded_to_4_decimal_places(self, sample_analysis):
        value = str(sample_analysis.to_dict()["key_confidence"])
        parts = value.split(".")
        if len(parts) == 2:
            assert len(parts[1]) <= 4

    def test_duration_rounded_to_2_decimal_places(self, sample_analysis):
        value = str(sample_analysis.to_dict()["duration_seconds"])
        parts = value.split(".")
        if len(parts) == 2:
            assert len(parts[1]) <= 2


class TestMusicAnalysisProperties:
    def test_camelot_property(self, sample_analysis):
        assert sample_analysis.camelot == "8B"

    def test_openkey_property(self, sample_analysis):
        assert sample_analysis.openkey == "1d"

    def test_camelot_start_property(self, sample_analysis):
        assert sample_analysis.camelot_start == "8B"

    def test_camelot_end_property(self, sample_analysis):
        assert sample_analysis.camelot_end == "9B"

    def test_unknown_key_returns_question_mark(self):
        analysis = MusicAnalysis(
            key="X Invalid",
            key_confidence=0.0,
            key_start="X Invalid",
            start_confidence=0.0,
            key_end="X Invalid",
            end_confidence=0.0,
            bpm=0.0,
            duration_seconds=0.0,
        )
        assert analysis.camelot == "?"
        assert analysis.openkey == "?"
