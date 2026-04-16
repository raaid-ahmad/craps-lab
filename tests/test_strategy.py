"""Tests for the strategy layer primitives."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from craps_lab.bets import BetType
from craps_lab.dice import DiceRoll
from craps_lab.engine import Table
from craps_lab.strategy import (
    ActionType,
    BetAction,
    Context,
    Strategy,
    run_strategy,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


class ScriptedRoller:
    def __init__(self, rolls: Iterable[DiceRoll]) -> None:
        self._rolls = iter(rolls)

    def roll(self) -> DiceRoll:
        return next(self._rolls)


class TestBetAction:
    """Construction and validation of BetAction."""

    def test_place_factory(self) -> None:
        a = BetAction.place(BetType.PASS_LINE, 5)
        assert a.action is ActionType.PLACE
        assert a.kind is BetType.PASS_LINE
        assert a.amount == 5

    def test_place_with_number(self) -> None:
        a = BetAction.place(BetType.PLACE, 6, number=8)
        assert a.number == 8

    def test_place_with_linked_bet_id(self) -> None:
        a = BetAction.place(BetType.COME_ODDS, 10, linked_bet_id=3)
        assert a.linked_bet_id == 3

    def test_remove_factory(self) -> None:
        a = BetAction.remove(42)
        assert a.action is ActionType.REMOVE
        assert a.bet_id == 42

    def test_place_rejects_bet_id(self) -> None:
        with pytest.raises(ValueError, match="does not accept bet_id"):
            BetAction(
                action=ActionType.PLACE,
                kind=BetType.PASS_LINE,
                amount=5,
                bet_id=1,
            )

    def test_place_requires_kind(self) -> None:
        with pytest.raises(ValueError, match="requires kind"):
            BetAction(action=ActionType.PLACE, amount=5)

    def test_place_requires_amount(self) -> None:
        with pytest.raises(ValueError, match="requires amount"):
            BetAction(action=ActionType.PLACE, kind=BetType.PASS_LINE)

    def test_remove_requires_bet_id(self) -> None:
        with pytest.raises(ValueError, match="requires bet_id"):
            BetAction(action=ActionType.REMOVE)

    def test_remove_rejects_kind(self) -> None:
        with pytest.raises(ValueError, match="does not accept kind"):
            BetAction(
                action=ActionType.REMOVE,
                bet_id=1,
                kind=BetType.PASS_LINE,
            )


class TestContext:
    """Context is a frozen snapshot."""

    def test_construction(self) -> None:
        ctx = Context(
            point=6,
            active_bets=(),
            last_resolution=None,
            roll_number=1,
        )
        assert ctx.point == 6
        assert ctx.roll_number == 1

    def test_is_frozen(self) -> None:
        ctx = Context(point=None, active_bets=(), last_resolution=None, roll_number=1)
        with pytest.raises(AttributeError):
            ctx.point = 6  # type: ignore[misc]


class AlwaysPass(Strategy):
    """Minimal strategy: place a pass-line bet on every come-out."""

    def __init__(self, amount: int = 5) -> None:
        self._amount = amount

    def get_actions(self, ctx: Context) -> Sequence[BetAction]:
        has_pass = any(b.kind is BetType.PASS_LINE for b in ctx.active_bets)
        if ctx.point is None and not has_pass:
            return [BetAction.place(BetType.PASS_LINE, self._amount)]
        return []


class TestRunStrategy:
    """Integration tests for run_strategy with a minimal strategy."""

    def test_returns_correct_number_of_rolls(self) -> None:
        table = Table(seed=42)
        results = run_strategy(AlwaysPass(), table, max_rolls=10)
        assert len(results) == 10

    def test_pass_line_placed_on_come_out(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 4)]))
        results = run_strategy(AlwaysPass(), table, max_rolls=1)
        (res,) = results
        assert any(r.kind is BetType.PASS_LINE for r in res.resolutions)

    def test_context_carries_last_resolution(self) -> None:
        seen_contexts: list[Context] = []

        class Spy(Strategy):
            def get_actions(self, ctx: Context) -> Sequence[BetAction]:
                seen_contexts.append(ctx)
                has_pass = any(b.kind is BetType.PASS_LINE for b in ctx.active_bets)
                if ctx.point is None and not has_pass:
                    return [BetAction.place(BetType.PASS_LINE, 5)]
                return []

        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 2)]))
        run_strategy(Spy(), table, max_rolls=2)
        assert seen_contexts[0].last_resolution is None
        assert seen_contexts[0].roll_number == 1
        assert seen_contexts[1].last_resolution is not None
        assert seen_contexts[1].roll_number == 2

    def test_strategy_name_defaults_to_class_name(self) -> None:
        assert AlwaysPass().name == "AlwaysPass"
