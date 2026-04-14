"""Unit tests for the two-dice sum PMF and its tent-function counts."""

from __future__ import annotations

from fractions import Fraction

import pytest

from craps_lab.probability import (
    MAX_TWO_DICE_SUM,
    MIN_TWO_DICE_SUM,
    TWO_DICE_SAMPLE_SPACE_SIZE,
    two_dice_sum_count,
    two_dice_sum_pmf,
)

_ALL_TOTALS = list(range(MIN_TWO_DICE_SUM, MAX_TWO_DICE_SUM + 1))


def test_pmf_sums_exactly_to_one() -> None:
    pmf = two_dice_sum_pmf()
    assert sum(pmf.values()) == Fraction(1)


def test_pmf_values_are_all_positive() -> None:
    pmf = two_dice_sum_pmf()
    for total in _ALL_TOTALS:
        assert pmf[total] > 0


def test_pmf_is_symmetric_about_seven() -> None:
    pmf = two_dice_sum_pmf()
    for total in _ALL_TOTALS:
        assert pmf[total] == pmf[14 - total]


def test_pmf_mode_is_seven() -> None:
    pmf = two_dice_sum_pmf()
    mode_value = max(pmf.values())
    modes = [k for k, v in pmf.items() if v == mode_value]
    assert modes == [7]


def test_pmf_expected_value_equals_seven() -> None:
    pmf = two_dice_sum_pmf()
    expected_value = sum(total * prob for total, prob in pmf.items())
    assert expected_value == Fraction(7)


def test_pmf_probability_of_seven_is_one_sixth() -> None:
    pmf = two_dice_sum_pmf()
    assert pmf[7] == Fraction(1, 6)


@pytest.mark.parametrize(
    ("total", "expected_count"),
    [
        (2, 1),
        (3, 2),
        (4, 3),
        (5, 4),
        (6, 5),
        (7, 6),
        (8, 5),
        (9, 4),
        (10, 3),
        (11, 2),
        (12, 1),
    ],
)
def test_count_tent_function(total: int, expected_count: int) -> None:
    assert two_dice_sum_count(total) == expected_count


@pytest.mark.parametrize("out_of_range", [0, 1, 13, 14, -5, 100])
def test_count_outside_range_is_zero(out_of_range: int) -> None:
    assert two_dice_sum_count(out_of_range) == 0


def test_sum_of_counts_equals_sample_space_size() -> None:
    total_counts = sum(two_dice_sum_count(s) for s in _ALL_TOTALS)
    assert total_counts == TWO_DICE_SAMPLE_SPACE_SIZE


def test_pmf_matches_count_over_sample_space_size() -> None:
    pmf = two_dice_sum_pmf()
    for total in _ALL_TOTALS:
        expected = Fraction(two_dice_sum_count(total), TWO_DICE_SAMPLE_SPACE_SIZE)
        assert pmf[total] == expected
