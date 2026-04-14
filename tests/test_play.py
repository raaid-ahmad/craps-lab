"""Unit tests for ``play_pass_line`` and ``play_dont_pass``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from craps_lab.bets import Outcome
from craps_lab.dice import DiceRoll, DiceRoller
from craps_lab.play import play_dont_pass, play_pass_line

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
