"""
Tests for music_analyzer.camelot module.
"""

import pytest
from music_analyzer.camelot import (
    TOM_PARA_CAMELOT,
    CAMELOT_PARA_TOM,
    TOM_PARA_OPENKEY,
    obter_camelot,
    obter_openkey,
    _distancia_circular,
    compatibilidade,
    sugerir_proximas,
)


# ── obter_camelot ────────────────────────────────────────────────

class TestObterCamelot:
    def test_c_major(self):
        assert obter_camelot("C Major") == "8B"

    def test_a_minor(self):
        assert obter_camelot("A Minor") == "8A"

    def test_all_24_keys_return_a_value(self):
        for tom in TOM_PARA_CAMELOT:
            assert obter_camelot(tom) is not None

    def test_unknown_key_returns_none(self):
        assert obter_camelot("X Unknown") is None

    def test_empty_string_returns_none(self):
        assert obter_camelot("") is None

    def test_camelot_codes_are_unique(self):
        codes = list(TOM_PARA_CAMELOT.values())
        assert len(codes) == len(set(codes))

    def test_camelot_inverse_mapping_consistent(self):
        for tom, code in TOM_PARA_CAMELOT.items():
            assert CAMELOT_PARA_TOM[code] == tom


# ── obter_openkey ────────────────────────────────────────────────

class TestObterOpenkey:
    def test_c_major(self):
        assert obter_openkey("C Major") == "1d"

    def test_a_minor(self):
        assert obter_openkey("A Minor") == "1m"

    def test_all_24_keys_return_a_value(self):
        for tom in TOM_PARA_OPENKEY:
            assert obter_openkey(tom) is not None

    def test_unknown_key_returns_none(self):
        assert obter_openkey("Z# Major") is None

    def test_openkey_codes_are_unique(self):
        codes = list(TOM_PARA_OPENKEY.values())
        assert len(codes) == len(set(codes))

    def test_covers_all_24_tonalities(self):
        assert len(TOM_PARA_OPENKEY) == 24


# ── _distancia_circular ──────────────────────────────────────────

class TestDistanciaCircular:
    def test_same_position_is_zero(self):
        assert _distancia_circular(5, 5) == 0

    def test_adjacent_is_one(self):
        assert _distancia_circular(1, 2) == 1
        assert _distancia_circular(2, 1) == 1

    def test_opposite_side_of_ring(self):
        # 1 and 7 in a ring of 12: min(6, 6) = 6
        assert _distancia_circular(1, 7) == 6

    def test_wrap_around(self):
        # 1 and 12 in ring of 12: min(11, 1) = 1
        assert _distancia_circular(1, 12) == 1

    def test_symmetry(self):
        assert _distancia_circular(3, 9) == _distancia_circular(9, 3)

    def test_max_distance_is_half_modulo(self):
        assert _distancia_circular(1, 7, 12) == 6
        assert _distancia_circular(1, 8, 12) == 5


# ── compatibilidade ──────────────────────────────────────────────

class TestCompatibilidade:
    def test_same_key_is_perfeita(self):
        r = compatibilidade("C Major", "C Major")
        assert r["nivel"] == "perfeita"
        assert r["distancia"] == 0

    def test_relative_minor_is_perfeita(self):
        # C Major (8B) and A Minor (8A) — same number, different letter
        r = compatibilidade("C Major", "A Minor")
        assert r["nivel"] == "perfeita"
        assert "relativa" in r["descricao"].lower()

    def test_neighbor_same_letter_is_boa(self):
        # C Major (8B) and G Major (9B): dist=1, same letter
        r = compatibilidade("C Major", "G Major")
        assert r["nivel"] == "boa"
        assert r["distancia"] == 1

    def test_neighbor_different_letter_is_boa(self):
        # G Major (9B) and E Minor (9A): dist=0, diff letter — perfeita (relative)
        # Use a case that is dist=1 AND different letter
        # C Major (8B) and E Minor (9A): dist=1, letters B vs A
        r = compatibilidade("C Major", "E Minor")
        assert r["nivel"] == "boa"

    def test_distance_2_is_arriscada(self):
        # C Major (8B), D Major (10B): dist=2
        r = compatibilidade("C Major", "D Major")
        assert r["nivel"] == "arriscada"
        assert r["distancia"] == 2

    def test_distance_7_is_unreachable_via_circular_distance(self):
        # _distancia_circular with modulo=12 returns at most 6.
        # The dist==7 branch in compatibilidade() is dead code for a 12-position ring.
        # Verify that no valid Camelot pair can produce dist==7.
        from music_analyzer.camelot import CAMELOT_PARA_TOM
        all_keys = list(TOM_PARA_CAMELOT.keys())
        for tom_a in all_keys:
            r = compatibilidade(tom_a, all_keys[-1])
            assert r["distancia"] <= 6

    def test_large_distance_is_incompativel(self):
        # 1B and 5B: dist=4
        from music_analyzer.camelot import CAMELOT_PARA_TOM
        tom_1b = CAMELOT_PARA_TOM["1B"]
        tom_5b = CAMELOT_PARA_TOM["5B"]
        r = compatibilidade(tom_1b, tom_5b)
        assert r["nivel"] == "incompativel"

    def test_unknown_key_a_returns_desconhecida(self):
        r = compatibilidade("X# Major", "C Major")
        assert r["nivel"] == "desconhecida"
        assert r["distancia"] == -1

    def test_unknown_key_b_returns_desconhecida(self):
        r = compatibilidade("C Major", "Y Minor")
        assert r["nivel"] == "desconhecida"
        assert r["distancia"] == -1

    def test_both_unknown_returns_desconhecida(self):
        r = compatibilidade("X Major", "Y Minor")
        assert r["nivel"] == "desconhecida"

    def test_return_dict_has_required_keys(self):
        r = compatibilidade("C Major", "G Major")
        for key in ("nivel", "descricao", "camelot_a", "camelot_b", "distancia"):
            assert key in r

    def test_camelot_codes_in_result(self):
        r = compatibilidade("C Major", "G Major")
        assert r["camelot_a"] == "8B"
        assert r["camelot_b"] == "9B"


# ── sugerir_proximas ─────────────────────────────────────────────

class TestSugerirProximas:
    def test_unknown_key_returns_empty(self):
        assert sugerir_proximas("Z Unknown") == []

    def test_returns_list_of_dicts(self):
        sug = sugerir_proximas("C Major")
        assert isinstance(sug, list)
        assert all(isinstance(s, dict) for s in sug)

    def test_each_suggestion_has_required_keys(self):
        sug = sugerir_proximas("C Major")
        for s in sug:
            for key in ("tom", "camelot", "nivel", "descricao"):
                assert key in s

    def test_c_major_has_relative_minor(self):
        sug = sugerir_proximas("C Major")
        toms = [s["tom"] for s in sug]
        assert "A Minor" in toms

    def test_relative_suggestion_is_perfeita(self):
        sug = sugerir_proximas("C Major")
        rel = next(s for s in sug if s["tom"] == "A Minor")
        assert rel["nivel"] == "perfeita"

    def test_neighbors_are_boa(self):
        sug = sugerir_proximas("C Major")
        boa = [s for s in sug if s["nivel"] == "boa"]
        assert len(boa) >= 2

    def test_no_self_suggestion(self):
        sug = sugerir_proximas("C Major")
        toms = [s["tom"] for s in sug]
        assert "C Major" not in toms

    def test_a_minor_suggestions(self):
        # A Minor (8A) — relative is C Major (8B)
        sug = sugerir_proximas("A Minor")
        toms = [s["tom"] for s in sug]
        assert "C Major" in toms

    def test_b_major_wrap_around(self):
        # B Major is 1B — neighbor below wraps to 12B
        sug = sugerir_proximas("B Major")
        toms = [s["tom"] for s in sug]
        from music_analyzer.camelot import CAMELOT_PARA_TOM
        assert CAMELOT_PARA_TOM["12B"] in toms

    def test_suggestion_camelot_codes_are_valid(self):
        for tom in TOM_PARA_CAMELOT:
            sug = sugerir_proximas(tom)
            for s in sug:
                assert s["camelot"] in CAMELOT_PARA_TOM
