"""Unit tests for ``play_pass_line`` and ``play_dont_pass``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from craps_lab.bets import Outcome
from craps_lab.dice import DiceRoll, DiceRoller
from craps_lab.play import (
    play_come_bet,
    play_dont_come_bet,
    play_dont_pass,
    play_pass_line,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class _ScriptedRoller:
    """Test-only ``RollSource`` that returns a pre-specified sequence.

    Satisfies the structural ``RollSource`` protocol in
    ``craps_lab.play`` without inheriting from ``DiceRoller``. Used to
    drive every branch of the play runners deterministically.
    """

    def __init__(self, rolls: list[tuple[int, int]]) -> None:
        self._iter: Iterator[tuple[int, int]] = iter(rolls)

    def roll(self) -> DiceRoll:
        d1, d2 = next(self._iter)
        return DiceRoll(d1, d2)


@pytest.mark.parametrize(("d1", "d2"), [(3, 4), (6, 5)])  # 7, 11
def test_play_pass_line_naturals_win(d1: int, d2: int) -> None:
    roller = _ScriptedRoller([(d1, d2)])
    assert play_pass_line(roller) == Outcome.WIN


@pytest.mark.parametrize(("d1", "d2"), [(1, 1), (1, 2), (6, 6)])  # 2, 3, 12
def test_play_pass_line_craps_lose(d1: int, d2: int) -> None:
    roller = _ScriptedRoller([(d1, d2)])
    assert play_pass_line(roller) == Outcome.LOSE


def test_play_pass_line_point_then_point_wins() -> None:
    # Point 6 established, then rolled 6 again → win.
    roller = _ScriptedRoller([(3, 3), (2, 4)])
    assert play_pass_line(roller) == Outcome.WIN


def test_play_pass_line_point_then_seven_loses() -> None:
    # Point 9 established, then seven-out → lose.
    roller = _ScriptedRoller([(4, 5), (4, 3)])
    assert play_pass_line(roller) == Outcome.LOSE


def test_play_pass_line_intermediate_rolls_are_ignored() -> None:
    # Point 8, non-resolving 5 and 3, then 8 → win.
    roller = _ScriptedRoller([(4, 4), (2, 3), (1, 2), (5, 3)])
    assert play_pass_line(roller) == Outcome.WIN


@pytest.mark.parametrize(("d1", "d2"), [(1, 1), (1, 2)])  # 2, 3
def test_play_dont_pass_come_out_wins(d1: int, d2: int) -> None:
    roller = _ScriptedRoller([(d1, d2)])
    assert play_dont_pass(roller) == Outcome.WIN


@pytest.mark.parametrize(("d1", "d2"), [(3, 4), (6, 5)])  # 7, 11
def test_play_dont_pass_come_out_loses(d1: int, d2: int) -> None:
    roller = _ScriptedRoller([(d1, d2)])
    assert play_dont_pass(roller) == Outcome.LOSE


def test_play_dont_pass_come_out_twelve_pushes() -> None:
    roller = _ScriptedRoller([(6, 6)])
    assert play_dont_pass(roller) == Outcome.PUSH


def test_play_dont_pass_point_then_seven_wins() -> None:
    # Point 9 established, then 7 → don't pass wins on the seven-out.
    roller = _ScriptedRoller([(4, 5), (4, 3)])
    assert play_dont_pass(roller) == Outcome.WIN


def test_play_dont_pass_point_then_point_loses() -> None:
    # Point 9 established, then 9 again → don't pass loses.
    roller = _ScriptedRoller([(4, 5), (3, 6)])
    assert play_dont_pass(roller) == Outcome.LOSE


def test_play_pass_line_with_real_roller_is_deterministic_under_seed() -> None:
    a = DiceRoller(seed=42)
    b = DiceRoller(seed=42)
    assert play_pass_line(a) == play_pass_line(b)


def test_play_dont_pass_with_real_roller_is_deterministic_under_seed() -> None:
    a = DiceRoller(seed=123)
    b = DiceRoller(seed=123)
    assert play_dont_pass(a) == play_dont_pass(b)


def test_play_come_bet_equivalent_to_play_pass_line_under_same_seed() -> None:
    # Over many games with the same seed, play_come_bet and
    # play_pass_line should produce identical outcomes in the same
    # order, because the former is a thin delegation to the latter.
    come_roller = DiceRoller(seed=0xC0C0)
    line_roller = DiceRoller(seed=0xC0C0)
    for _ in range(500):
        assert play_come_bet(come_roller) == play_pass_line(line_roller)


def test_play_dont_come_bet_equivalent_to_play_dont_pass_under_same_seed() -> None:
    come_roller = DiceRoller(seed=0xDEAD)
    line_roller = DiceRoller(seed=0xDEAD)
    for _ in range(500):
        assert play_dont_come_bet(come_roller) == play_dont_pass(line_roller)


# Branch coverage for play_come_bet / play_dont_come_bet on their own,
# not as a consequence of delegation. Exercising each branch through
# the come-bet function directly is what makes the "pass-line-style
# rules from the next roll" contract executable as a test rather than
# only as a docstring claim.


@pytest.mark.parametrize(("d1", "d2"), [(3, 4), (6, 5)])  # 7, 11
def test_play_come_bet_next_roll_naturals_win(d1: int, d2: int) -> None:
    roller = _ScriptedRoller([(d1, d2)])
    assert play_come_bet(roller) == Outcome.WIN


@pytest.mark.parametrize(("d1", "d2"), [(1, 1), (1, 2), (6, 6)])  # 2, 3, 12
def test_play_come_bet_next_roll_craps_lose(d1: int, d2: int) -> None:
    roller = _ScriptedRoller([(d1, d2)])
    assert play_come_bet(roller) == Outcome.LOSE


def test_play_come_bet_come_point_then_point_wins() -> None:
    # Come point 5 established on the next roll, then 5 again → win.
    roller = _ScriptedRoller([(2, 3), (4, 1)])
    assert play_come_bet(roller) == Outcome.WIN


def test_play_come_bet_come_point_then_seven_loses() -> None:
    # Come point 8 established, then seven-out → lose.
    roller = _ScriptedRoller([(2, 6), (4, 3)])
    assert play_come_bet(roller) == Outcome.LOSE


def test_play_come_bet_intermediate_rolls_are_ignored() -> None:
    # Come point 9, non-resolving 4 and 10, then 9 → win.
    roller = _ScriptedRoller([(4, 5), (1, 3), (4, 6), (3, 6)])
    assert play_come_bet(roller) == Outcome.WIN


@pytest.mark.parametrize(("d1", "d2"), [(1, 1), (1, 2)])  # 2, 3
def test_play_dont_come_bet_next_roll_wins(d1: int, d2: int) -> None:
    roller = _ScriptedRoller([(d1, d2)])
    assert play_dont_come_bet(roller) == Outcome.WIN


@pytest.mark.parametrize(("d1", "d2"), [(3, 4), (6, 5)])  # 7, 11
def test_play_dont_come_bet_next_roll_loses(d1: int, d2: int) -> None:
    roller = _ScriptedRoller([(d1, d2)])
    assert play_dont_come_bet(roller) == Outcome.LOSE


def test_play_dont_come_bet_next_roll_twelve_pushes() -> None:
    # Bar 12: a come-out 12 on the next roll pushes rather than losing.
    roller = _ScriptedRoller([(6, 6)])
    assert play_dont_come_bet(roller) == Outcome.PUSH


def test_play_dont_come_bet_come_point_then_seven_wins() -> None:
    # Come point 6 established, then seven-out → don't-come wins.
    roller = _ScriptedRoller([(3, 3), (2, 5)])
    assert play_dont_come_bet(roller) == Outcome.WIN


def test_play_dont_come_bet_come_point_then_point_loses() -> None:
    # Come point 10 established, then 10 again → don't-come loses.
    roller = _ScriptedRoller([(4, 6), (5, 5)])
    assert play_dont_come_bet(roller) == Outcome.LOSE
