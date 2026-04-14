"""Unit tests for ``Outcome``, ``BetType``, and the line-bet rule constants."""

from __future__ import annotations

from fractions import Fraction

from craps_lab.bets import (
    DONT_PASS_BAR,
    DONT_PASS_COME_OUT_LOSES,
    DONT_PASS_COME_OUT_WINS,
    DONT_PASS_LAY_PAYOUT_RATIO,
    PASS_LINE_CRAPS_LOSERS,
    PASS_LINE_NATURAL_WINNERS,
    PASS_ODDS_PAYOUT_RATIO,
    POINT_NUMBERS,
    SEVEN,
    BetType,
    Outcome,
)

_ALL_SUMS = set(range(2, 13))


def test_outcome_values() -> None:
    assert Outcome.WIN.value == "win"
    assert Outcome.LOSE.value == "lose"
    assert Outcome.PUSH.value == "push"


def test_outcome_is_subclass_of_str() -> None:
    assert isinstance(Outcome.WIN, str)
    assert str(Outcome.WIN) == "win"


def test_bet_type_values() -> None:
    assert BetType.PASS_LINE.value == "pass_line"
    assert BetType.DONT_PASS.value == "dont_pass"
    assert BetType.COME.value == "come"
    assert BetType.DONT_COME.value == "dont_come"
    assert BetType.PASS_ODDS.value == "pass_odds"
    assert BetType.DONT_PASS_ODDS.value == "dont_pass_odds"
    assert BetType.COME_ODDS.value == "come_odds"
    assert BetType.DONT_COME_ODDS.value == "dont_come_odds"


def test_pass_odds_payout_ratio_has_every_point() -> None:
    assert set(PASS_ODDS_PAYOUT_RATIO.keys()) == set(POINT_NUMBERS)


def test_pass_odds_payout_ratio_values() -> None:
    # 4 and 10: 2:1 (3 winning combinations vs. 6 losing)
    assert PASS_ODDS_PAYOUT_RATIO[4] == Fraction(2, 1)
    assert PASS_ODDS_PAYOUT_RATIO[10] == Fraction(2, 1)
    # 5 and 9: 3:2
    assert PASS_ODDS_PAYOUT_RATIO[5] == Fraction(3, 2)
    assert PASS_ODDS_PAYOUT_RATIO[9] == Fraction(3, 2)
    # 6 and 8: 6:5
    assert PASS_ODDS_PAYOUT_RATIO[6] == Fraction(6, 5)
    assert PASS_ODDS_PAYOUT_RATIO[8] == Fraction(6, 5)


def test_dont_pass_lay_payout_ratio_has_every_point() -> None:
    assert set(DONT_PASS_LAY_PAYOUT_RATIO.keys()) == set(POINT_NUMBERS)


def test_dont_pass_lay_payout_ratio_is_inverse_of_pass_odds() -> None:
    for point in POINT_NUMBERS:
        pass_payout = PASS_ODDS_PAYOUT_RATIO[point]
        lay_payout = DONT_PASS_LAY_PAYOUT_RATIO[point]
        assert lay_payout == Fraction(1) / pass_payout


def test_seven_constant() -> None:
    assert SEVEN == 7


def test_point_numbers_are_the_canonical_six() -> None:
    assert set(POINT_NUMBERS) == {4, 5, 6, 8, 9, 10}
    assert len(POINT_NUMBERS) == 6


def test_pass_line_come_out_rules_partition_all_sums() -> None:
    naturals = PASS_LINE_NATURAL_WINNERS
    losers = PASS_LINE_CRAPS_LOSERS
    points = set(POINT_NUMBERS)

    assert naturals | losers | points == _ALL_SUMS
    assert not (naturals & losers)
    assert not (naturals & points)
    assert not (losers & points)


def test_dont_pass_come_out_rules_partition_all_sums() -> None:
    wins = DONT_PASS_COME_OUT_WINS
    loses = DONT_PASS_COME_OUT_LOSES
    bar = {DONT_PASS_BAR}
    points = set(POINT_NUMBERS)

    assert wins | loses | bar | points == _ALL_SUMS
    assert not (wins & loses)
    assert not (wins & bar)
    assert not (loses & bar)
    assert not (wins & points)
    assert not (loses & points)
    assert not (bar & points)


def test_dont_pass_bar_is_twelve() -> None:
    assert DONT_PASS_BAR == 12
