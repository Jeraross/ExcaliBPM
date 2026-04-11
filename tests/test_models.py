"""
Tests for music_analyzer.models module.
"""

import pytest
from music_analyzer.models import AnaliseMusical


def _make_analise(**kwargs) -> AnaliseMusical:
    defaults = dict(
        tonalidade_geral="C Major",
        confianca_geral=0.85,
        tonalidade_inicio="C Major",
        confianca_inicio=0.80,
        tonalidade_final="C Major",
        confianca_final=0.90,
        bpm=128.0,
        duracao_segundos=210.0,
        arquivo="test_track.wav",
        votos_perfis={"bellman_budge": "C Major"},
        votos_frames=["C Major", "C Major", "A Minor"],
    )
    defaults.update(kwargs)
    return AnaliseMusical(**defaults)


class TestCamelotProperty:
    def test_c_major_returns_8b(self):
        a = _make_analise(tonalidade_geral="C Major")
        assert a.camelot == "8B"

    def test_a_minor_returns_8a(self):
        a = _make_analise(tonalidade_geral="A Minor")
        assert a.camelot == "8A"

    def test_unknown_key_returns_question_mark(self):
        a = _make_analise(tonalidade_geral="X Unknown")
        assert a.camelot == "?"


class TestOpenKeyProperty:
    def test_c_major_returns_1d(self):
        a = _make_analise(tonalidade_geral="C Major")
        assert a.openkey == "1d"

    def test_a_minor_returns_1m(self):
        a = _make_analise(tonalidade_geral="A Minor")
        assert a.openkey == "1m"

    def test_unknown_key_returns_question_mark(self):
        a = _make_analise(tonalidade_geral="Z Major")
        assert a.openkey == "?"


class TestCamelotInicioProperty:
    def test_c_major_inicio_returns_8b(self):
        a = _make_analise(tonalidade_inicio="C Major")
        assert a.camelot_inicio == "8B"

    def test_unknown_inicio_returns_question_mark(self):
        a = _make_analise(tonalidade_inicio="Unknown")
        assert a.camelot_inicio == "?"


class TestCamelotFinalProperty:
    def test_c_major_final_returns_8b(self):
        a = _make_analise(tonalidade_final="C Major")
        assert a.camelot_final == "8B"

    def test_g_major_final_returns_9b(self):
        a = _make_analise(tonalidade_final="G Major")
        assert a.camelot_final == "9B"

    def test_unknown_final_returns_question_mark(self):
        a = _make_analise(tonalidade_final="??")
        assert a.camelot_final == "?"


class TestStr:
    def test_returns_string(self):
        a = _make_analise()
        assert isinstance(str(a), str)

    def test_contains_bpm(self):
        a = _make_analise(bpm=128.0)
        assert "128.0" in str(a)

    def test_contains_key(self):
        a = _make_analise(tonalidade_geral="G Major")
        assert "G Major" in str(a)

    def test_contains_filename(self):
        a = _make_analise(arquivo="my_track.wav")
        assert "my_track.wav" in str(a)

    def test_no_filename_when_empty(self):
        a = _make_analise(arquivo="")
        text = str(a)
        # The empty arquivo line should be omitted from the output
        assert "  \n" not in text  # blank archivo line stripped

    def test_duration_minutes_seconds(self):
        # 210 seconds = 3:30
        a = _make_analise(duracao_segundos=210.0)
        text = str(a)
        assert "3:30" in text

    def test_duration_zero(self):
        a = _make_analise(duracao_segundos=0.0)
        text = str(a)
        assert "0:00" in text

    def test_contains_camelot_code(self):
        a = _make_analise(tonalidade_geral="C Major")
        assert "8B" in str(a)

    def test_contains_confidence_percentage(self):
        a = _make_analise(confianca_geral=0.85)
        assert "85%" in str(a)


class TestToDict:
    def test_returns_dict(self):
        a = _make_analise()
        assert isinstance(a.to_dict(), dict)

    def test_required_keys_present(self):
        a = _make_analise()
        d = a.to_dict()
        expected_keys = {
            "arquivo", "duracao_segundos", "bpm",
            "tonalidade_geral", "camelot", "openkey", "confianca_geral",
            "tonalidade_inicio", "camelot_inicio", "confianca_inicio",
            "tonalidade_final", "camelot_final", "confianca_final",
        }
        assert set(d.keys()) == expected_keys

    def test_bpm_value(self):
        a = _make_analise(bpm=130.5)
        assert a.to_dict()["bpm"] == 130.5

    def test_arquivo_value(self):
        a = _make_analise(arquivo="song.mp3")
        assert a.to_dict()["arquivo"] == "song.mp3"

    def test_camelot_in_dict(self):
        a = _make_analise(tonalidade_geral="C Major")
        assert a.to_dict()["camelot"] == "8B"

    def test_openkey_in_dict(self):
        a = _make_analise(tonalidade_geral="C Major")
        assert a.to_dict()["openkey"] == "1d"

    def test_confianca_rounded_to_4_decimals(self):
        a = _make_analise(confianca_geral=0.123456789)
        d = a.to_dict()
        assert d["confianca_geral"] == round(0.123456789, 4)

    def test_duracao_rounded_to_2_decimals(self):
        a = _make_analise(duracao_segundos=210.123456)
        d = a.to_dict()
        assert d["duracao_segundos"] == round(210.123456, 2)

    def test_round_trip_keys_are_serialisable(self):
        import json
        a = _make_analise()
        # Should not raise a serialisation error
        json.dumps(a.to_dict())
