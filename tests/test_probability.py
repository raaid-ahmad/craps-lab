"""Unit tests for the two-dice sum PMF and its tent-function counts."""

from __future__ import annotations

from fractions import Fraction

import pytest

from craps_lab.bets import POINT_NUMBERS
from craps_lab.probability import (
    LAY_3_4_5X,
    MAX_TWO_DICE_SUM,
    MIN_TWO_DICE_SUM,
    ODDS_3_4_5X,
    TWO_DICE_SAMPLE_SPACE_SIZE,
    come_bet_house_edge,
    come_bet_win_probability,
    dont_come_bet_house_edge,
    dont_come_bet_push_probability,
    dont_come_bet_win_probability,
    dont_pass_house_edge,
    dont_pass_lay_odds_expected_value,
    dont_pass_plus_lay_odds_edge,
    dont_pass_push_probability,
    dont_pass_win_probability,
    pass_line_house_edge,
    pass_line_plus_odds_edge,
    pass_line_win_probability,
    pass_odds_expected_value,
    probability_point_before_seven,
    two_dice_sum_count,
    two_dice_sum_pmf,
    uniform_odds_policy,
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


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        (4, Fraction(3, 9)),
        (5, Fraction(4, 10)),
        (6, Fraction(5, 11)),
        (8, Fraction(5, 11)),
        (9, Fraction(4, 10)),
        (10, Fraction(3, 9)),
    ],
)
def test_probability_point_before_seven_per_point(
    point: int,
    expected: Fraction,
) -> None:
    assert probability_point_before_seven(point) == expected


def test_probability_point_before_seven_is_symmetric_about_seven() -> None:
    assert probability_point_before_seven(4) == probability_point_before_seven(10)
    assert probability_point_before_seven(5) == probability_point_before_seven(9)
    assert probability_point_before_seven(6) == probability_point_before_seven(8)


@pytest.mark.parametrize("bad", [1, 7, 11, 12, 13, 0, -1])
def test_probability_point_before_seven_rejects_non_points(bad: int) -> None:
    with pytest.raises(ValueError, match="point must be one of"):
        probability_point_before_seven(bad)


def test_pass_line_win_probability_is_exactly_244_over_495() -> None:
    assert pass_line_win_probability() == Fraction(244, 495)


def test_pass_line_house_edge_is_exactly_7_over_495() -> None:
    assert pass_line_house_edge() == Fraction(7, 495)


def test_pass_line_house_edge_matches_canonical_percentage() -> None:
    edge = float(pass_line_house_edge())
    assert 0.01413 < edge < 0.01415  # canonical 1.414%


def test_pass_line_win_and_lose_sum_to_one() -> None:
    win = pass_line_win_probability()
    lose = Fraction(1) - win
    assert win + lose == Fraction(1)


def test_dont_pass_win_probability_is_exactly_949_over_1980() -> None:
    assert dont_pass_win_probability() == Fraction(949, 1980)


def test_dont_pass_push_probability_is_exactly_one_thirty_sixth() -> None:
    assert dont_pass_push_probability() == Fraction(1, 36)


def test_dont_pass_house_edge_is_exactly_3_over_220() -> None:
    assert dont_pass_house_edge() == Fraction(3, 220)


def test_dont_pass_house_edge_matches_canonical_percentage() -> None:
    edge = float(dont_pass_house_edge())
    assert 0.01363 < edge < 0.01365  # canonical 1.364%


def test_dont_pass_win_plus_push_plus_lose_equals_one() -> None:
    win = dont_pass_win_probability()
    push = dont_pass_push_probability()
    lose = Fraction(1) - win - push
    assert win + push + lose == Fraction(1)


def test_pass_win_plus_dont_win_plus_dont_push_equals_one() -> None:
    # Cross-check: pass line wins iff don't pass loses (not pushes),
    # so P(pass win) + P(dont win) + P(dont push) must equal 1.
    pass_win = pass_line_win_probability()
    dont_win = dont_pass_win_probability()
    dont_push = dont_pass_push_probability()
    assert pass_win + dont_win + dont_push == Fraction(1)


def test_dont_pass_edge_is_lower_than_pass_line_edge() -> None:
    assert dont_pass_house_edge() < pass_line_house_edge()


def test_come_bet_win_probability_equals_pass_line() -> None:
    assert come_bet_win_probability() == pass_line_win_probability()


def test_come_bet_house_edge_equals_pass_line() -> None:
    assert come_bet_house_edge() == pass_line_house_edge()


def test_come_bet_house_edge_is_exactly_7_over_495() -> None:
    assert come_bet_house_edge() == Fraction(7, 495)


def test_come_bet_win_probability_derived_from_pmf() -> None:
    # Rebuild P(come bet wins) directly from the PMF and the per-point
    # geometric process, without calling pass_line_win_probability.
    # The equivalence to pass line then falls out as a derived fact
    # rather than the delegation it is in the implementation — this is
    # what makes the "dice have no memory" argument executable.
    pmf = two_dice_sum_pmf()
    count_seven = two_dice_sum_count(7)
    naturals = pmf[7] + pmf[11]
    come_point_wins = sum(
        (
            pmf[p] * Fraction(two_dice_sum_count(p), two_dice_sum_count(p) + count_seven)
            for p in POINT_NUMBERS
        ),
        start=Fraction(0),
    )
    derived = naturals + come_point_wins
    assert derived == Fraction(244, 495)
    assert come_bet_win_probability() == derived


def test_dont_come_bet_win_probability_equals_dont_pass() -> None:
    assert dont_come_bet_win_probability() == dont_pass_win_probability()


def test_dont_come_bet_push_equals_dont_pass_push() -> None:
    assert dont_come_bet_push_probability() == dont_pass_push_probability()


def test_dont_come_bet_house_edge_equals_dont_pass() -> None:
    assert dont_come_bet_house_edge() == dont_pass_house_edge()


def test_dont_come_bet_house_edge_is_exactly_3_over_220() -> None:
    assert dont_come_bet_house_edge() == Fraction(3, 220)


def test_dont_come_bet_win_probability_derived_from_pmf() -> None:
    # Same no-memory check on the don't-come side, independently of
    # dont_pass_win_probability. The bar-12 rule applies: 2 and 3 win,
    # 12 pushes, 7 and 11 lose on the come-out; point 4-10 resolves by
    # the same geometric process and the don't-come wins if the seven
    # beats the point.
    pmf = two_dice_sum_pmf()
    count_seven = two_dice_sum_count(7)
    come_out_wins = pmf[2] + pmf[3]
    point_wins = sum(
        (
            pmf[p] * Fraction(count_seven, two_dice_sum_count(p) + count_seven)
            for p in POINT_NUMBERS
        ),
        start=Fraction(0),
    )
    derived = come_out_wins + point_wins
    assert derived == Fraction(949, 1980)
    assert dont_come_bet_win_probability() == derived


@pytest.mark.parametrize("point", list(POINT_NUMBERS))
def test_pass_odds_expected_value_is_exactly_zero(point: int) -> None:
    assert pass_odds_expected_value(point) == Fraction(0)


@pytest.mark.parametrize("point", list(POINT_NUMBERS))
def test_dont_pass_lay_odds_expected_value_is_exactly_zero(point: int) -> None:
    assert dont_pass_lay_odds_expected_value(point) == Fraction(0)


@pytest.mark.parametrize("bad", [1, 7, 11, 12, 13, 0])
def test_pass_odds_expected_value_rejects_non_points(bad: int) -> None:
    with pytest.raises(ValueError, match="point must be one of"):
        pass_odds_expected_value(bad)


@pytest.mark.parametrize("bad", [1, 7, 11, 12, 13, 0])
def test_dont_pass_lay_odds_expected_value_rejects_non_points(bad: int) -> None:
    with pytest.raises(ValueError, match="point must be one of"):
        dont_pass_lay_odds_expected_value(bad)


def test_uniform_odds_policy_has_same_value_at_every_point() -> None:
    policy = uniform_odds_policy(3)
    for point in POINT_NUMBERS:
        assert policy[point] == Fraction(3)


def test_uniform_odds_policy_accepts_fraction() -> None:
    policy = uniform_odds_policy(Fraction(5, 2))
    for point in POINT_NUMBERS:
        assert policy[point] == Fraction(5, 2)


def test_odds_3_4_5x_values() -> None:
    assert ODDS_3_4_5X[4] == Fraction(3)
    assert ODDS_3_4_5X[10] == Fraction(3)
    assert ODDS_3_4_5X[5] == Fraction(4)
    assert ODDS_3_4_5X[9] == Fraction(4)
    assert ODDS_3_4_5X[6] == Fraction(5)
    assert ODDS_3_4_5X[8] == Fraction(5)


def test_pass_line_plus_zero_odds_equals_pass_line_edge() -> None:
    assert pass_line_plus_odds_edge(uniform_odds_policy(0)) == pass_line_house_edge()


def test_pass_line_plus_1x_odds_is_exactly_7_over_825() -> None:
    """E[odds] = 1 * 24/36 = 2/3, total = 5/3, edge = (7/495)/(5/3) = 7/825."""
    assert pass_line_plus_odds_edge(uniform_odds_policy(1)) == Fraction(7, 825)


def test_pass_line_plus_2x_odds_is_exactly_1_over_165() -> None:
    """E[odds] = 2 * 24/36 = 4/3, total = 7/3, edge = (7/495)/(7/3) = 1/165."""
    assert pass_line_plus_odds_edge(uniform_odds_policy(2)) == Fraction(1, 165)


def test_pass_line_plus_3x_odds_is_exactly_7_over_1485() -> None:
    """E[odds] = 3 * 24/36 = 2, total = 3, edge = (7/495)/3 = 7/1485."""
    assert pass_line_plus_odds_edge(uniform_odds_policy(3)) == Fraction(7, 1485)


def test_pass_line_plus_3_4_5x_odds_is_exactly_7_over_1870() -> None:
    """E[odds] = 100/36 = 25/9 for 3-4-5x, total = 34/9, edge = 7/1870."""
    assert pass_line_plus_odds_edge(ODDS_3_4_5X) == Fraction(7, 1870)


def test_pass_line_plus_3_4_5x_odds_matches_canonical_percentage() -> None:
    edge = float(pass_line_plus_odds_edge(ODDS_3_4_5X))
    assert 0.00373 < edge < 0.00375  # canonical 0.374%


def test_pass_line_composite_edge_decreases_monotonically_with_odds() -> None:
    e0 = pass_line_plus_odds_edge(uniform_odds_policy(0))
    e1 = pass_line_plus_odds_edge(uniform_odds_policy(1))
    e2 = pass_line_plus_odds_edge(uniform_odds_policy(2))
    e3 = pass_line_plus_odds_edge(uniform_odds_policy(3))
    e5 = pass_line_plus_odds_edge(uniform_odds_policy(5))
    e10 = pass_line_plus_odds_edge(uniform_odds_policy(10))
    assert e0 > e1 > e2 > e3 > e5 > e10


def test_lay_3_4_5x_is_uniform_6x_at_every_point() -> None:
    for point in POINT_NUMBERS:
        assert LAY_3_4_5X[point] == Fraction(6)


def test_dont_pass_plus_zero_lay_equals_dont_pass_edge() -> None:
    zero_policy = uniform_odds_policy(0)
    assert dont_pass_plus_lay_odds_edge(zero_policy) == dont_pass_house_edge()


def test_dont_pass_plus_3_4_5x_lay_is_exactly_3_over_1100() -> None:
    """E[lay] = 6 * 24/36 = 4, total = 5, edge = (3/220)/5 = 3/1100."""
    assert dont_pass_plus_lay_odds_edge(LAY_3_4_5X) == Fraction(3, 1100)


def test_dont_pass_plus_3_4_5x_lay_matches_canonical_percentage() -> None:
    edge = float(dont_pass_plus_lay_odds_edge(LAY_3_4_5X))
    assert 0.00272 < edge < 0.00274  # canonical ~0.273%


def test_dont_pass_plus_lay_composite_is_lower_than_dont_pass_alone() -> None:
    assert dont_pass_plus_lay_odds_edge(LAY_3_4_5X) < dont_pass_house_edge()


def test_dont_pass_3_4_5x_lay_composite_is_lower_than_pass_3_4_5x_composite() -> None:
    # Don't pass with lay is *more* edge-efficient than pass with take
    # at 3-4-5x, because uniform 6x lay > the 25/9 average for 3-4-5x take.
    dp = dont_pass_plus_lay_odds_edge(LAY_3_4_5X)
    pl = pass_line_plus_odds_edge(ODDS_3_4_5X)
    assert dp < pl
