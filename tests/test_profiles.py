"""
Testes para music_analyzer.profiles — perfis de tonalidade.
"""

import numpy as np

from music_analyzer.profiles import PROFILES, PROFILES_EDM, get_all_profiles


class TestProfilesEstrutura:
    def test_profiles_tem_perfis_esperados(self):
        esperados = {
            "krumhansl_kessler", "temperley", "kostka_payne",
            "bellman_budge", "aarden_essen", "simple_sapp", "albrecht_shanahan",
        }
        assert esperados == set(PROFILES.keys())

    def test_profiles_edm_tem_shaath(self):
        assert "shaath" in PROFILES_EDM

    def test_cada_perfil_tem_major_e_minor(self):
        for nome, modos in {**PROFILES, **PROFILES_EDM}.items():
            assert "major" in modos, f"{nome} sem 'major'"
            assert "minor" in modos, f"{nome} sem 'minor'"

    def test_cada_perfil_tem_12_bins(self):
        for nome, modos in {**PROFILES, **PROFILES_EDM}.items():
            assert len(modos["major"]) == 12, f"{nome}.major não tem 12 elementos"
            assert len(modos["minor"]) == 12, f"{nome}.minor não tem 12 elementos"

    def test_perfis_tem_valores_positivos(self):
        for nome, modos in {**PROFILES, **PROFILES_EDM}.items():
            assert all(v >= 0 for v in modos["major"]), f"{nome}.major tem valor negativo"
            assert all(v >= 0 for v in modos["minor"]), f"{nome}.minor tem valor negativo"


class TestGetAllProfiles:
    def test_retorna_dict_nao_vazio(self):
        p = get_all_profiles()
        assert len(p) > 0

    def test_inclui_todos_os_perfis_gerais_e_edm(self):
        p = get_all_profiles()
        assert len(p) == len(PROFILES) + len(PROFILES_EDM)

    def test_valores_sao_numpy_arrays(self):
        p = get_all_profiles()
        for nome, modos in p.items():
            assert isinstance(modos["major"], np.ndarray), f"{nome}.major não é ndarray"
            assert isinstance(modos["minor"], np.ndarray), f"{nome}.minor não é ndarray"

    def test_dtype_float64(self):
        p = get_all_profiles()
        for nome, modos in p.items():
            assert modos["major"].dtype == np.float64, f"{nome}.major dtype errado"
            assert modos["minor"].dtype == np.float64, f"{nome}.minor dtype errado"

    def test_shape_correto(self):
        p = get_all_profiles()
        for nome, modos in p.items():
            assert modos["major"].shape == (12,)
            assert modos["minor"].shape == (12,)
