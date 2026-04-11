"""
Tests for music_analyzer.profiles module.
"""

import numpy as np
import pytest

from music_analyzer.profiles import PROFILES, PROFILES_EDM, get_all_profiles

EXPECTED_PROFILES = {
    "krumhansl_kessler",
    "temperley",
    "kostka_payne",
    "bellman_budge",
    "aarden_essen",
    "simple_sapp",
    "albrecht_shanahan",
}


class TestProfiles:
    def test_expected_profiles_present(self):
        assert set(PROFILES.keys()) == EXPECTED_PROFILES

    def test_profiles_have_major_and_minor(self):
        for name, modes in PROFILES.items():
            assert "major" in modes, f"{name} missing 'major'"
            assert "minor" in modes, f"{name} missing 'minor'"

    def test_profiles_have_12_values(self):
        for name, modes in PROFILES.items():
            for mode, values in modes.items():
                assert len(values) == 12, f"{name}/{mode} should have 12 values"

    def test_all_profile_values_are_non_negative(self):
        for name, modes in PROFILES.items():
            for mode, values in modes.items():
                for v in values:
                    assert v >= 0, f"{name}/{mode} has a negative value: {v}"


class TestProfilesEDM:
    def test_shaath_profile_exists(self):
        assert "shaath" in PROFILES_EDM

    def test_shaath_has_major_and_minor(self):
        assert "major" in PROFILES_EDM["shaath"]
        assert "minor" in PROFILES_EDM["shaath"]

    def test_shaath_has_12_values(self):
        for mode in ("major", "minor"):
            assert len(PROFILES_EDM["shaath"][mode]) == 12


class TestGetAllProfiles:
    def test_returns_dict(self):
        result = get_all_profiles()
        assert isinstance(result, dict)

    def test_includes_all_profiles_and_edm(self):
        result = get_all_profiles()
        expected = EXPECTED_PROFILES | {"shaath"}
        assert set(result.keys()) == expected

    def test_values_are_numpy_arrays(self):
        result = get_all_profiles()
        for name, modes in result.items():
            for mode, arr in modes.items():
                assert isinstance(arr, np.ndarray), f"{name}/{mode} is not ndarray"

    def test_arrays_are_float64(self):
        result = get_all_profiles()
        for name, modes in result.items():
            for mode, arr in modes.items():
                assert arr.dtype == np.float64, f"{name}/{mode} dtype is {arr.dtype}"

    def test_arrays_have_shape_12(self):
        result = get_all_profiles()
        for name, modes in result.items():
            for mode, arr in modes.items():
                assert arr.shape == (12,), f"{name}/{mode} shape is {arr.shape}"

    def test_original_dicts_not_mutated(self):
        get_all_profiles()
        # PROFILES should still contain plain Python lists
        for name, modes in PROFILES.items():
            for mode, values in modes.items():
                assert isinstance(values, list), f"{name}/{mode} was mutated"

    def test_total_count_is_8(self):
        result = get_all_profiles()
        assert len(result) == 8  # 7 general + 1 EDM
