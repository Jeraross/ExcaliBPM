"""
Tests for music_analyzer.profiles — key detection profiles.
"""

import numpy as np

from excalibpm.profiles import PROFILES, PROFILES_EDM, get_all_profiles


class TestProfilesStructure:
    def test_profiles_has_expected_entries(self):
        expected = {
            "krumhansl_kessler", "temperley", "kostka_payne",
            "bellman_budge", "aarden_essen", "simple_sapp", "albrecht_shanahan",
        }
        assert expected == set(PROFILES.keys())

    def test_edm_profiles_has_shaath(self):
        assert "shaath" in PROFILES_EDM

    def test_each_profile_has_major_and_minor(self):
        for name, modes in {**PROFILES, **PROFILES_EDM}.items():
            assert "major" in modes, f"{name} missing 'major'"
            assert "minor" in modes, f"{name} missing 'minor'"

    def test_each_profile_has_12_bins(self):
        for name, modes in {**PROFILES, **PROFILES_EDM}.items():
            assert len(modes["major"]) == 12, f"{name}.major does not have 12 elements"
            assert len(modes["minor"]) == 12, f"{name}.minor does not have 12 elements"

    def test_profiles_have_non_negative_values(self):
        for name, modes in {**PROFILES, **PROFILES_EDM}.items():
            assert all(v >= 0 for v in modes["major"]), f"{name}.major has negative value"
            assert all(v >= 0 for v in modes["minor"]), f"{name}.minor has negative value"


class TestGetAllProfiles:
    def test_returns_non_empty_dict(self):
        assert len(get_all_profiles()) > 0

    def test_includes_all_general_and_edm_profiles(self):
        p = get_all_profiles()
        assert len(p) == len(PROFILES) + len(PROFILES_EDM)

    def test_values_are_numpy_arrays(self):
        for name, modes in get_all_profiles().items():
            assert isinstance(modes["major"], np.ndarray), f"{name}.major is not ndarray"
            assert isinstance(modes["minor"], np.ndarray), f"{name}.minor is not ndarray"

    def test_dtype_is_float64(self):
        for name, modes in get_all_profiles().items():
            assert modes["major"].dtype == np.float64, f"{name}.major wrong dtype"
            assert modes["minor"].dtype == np.float64, f"{name}.minor wrong dtype"

    def test_shape_is_correct(self):
        for name, modes in get_all_profiles().items():
            assert modes["major"].shape == (12,)
            assert modes["minor"].shape == (12,)
