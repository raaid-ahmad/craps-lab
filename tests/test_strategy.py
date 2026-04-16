"""Tests for the strategy layer primitives."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from craps_lab.bets import BetType
from craps_lab.dice import DiceRoll
from craps_lab.engine import Table
from craps_lab.probability import ODDS_3_4_5X, pass_line_plus_odds_edge
from craps_lab.strategy import (
    ActionType,
    BetAction,
    Context,
    IronCross,
    PassLineWithOdds,
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


class TestPassLineWithOdds:
    """PassLineWithOdds places pass line on come-out and odds on point."""

    def test_places_pass_line_on_come_out(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        results = run_strategy(PassLineWithOdds(), table, max_rolls=1)
        assert any(b.kind is BetType.PASS_LINE for b in table.active_bets)
        assert results[0].point_after == 6

    def test_places_odds_after_point_established(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(2, 2)]))
        results = run_strategy(PassLineWithOdds(), table, max_rolls=2)
        assert results[0].point_after == 6
        assert any(b.kind is BetType.PASS_ODDS for b in table.active_bets)
        odds_bet = next(b for b in table.active_bets if b.kind is BetType.PASS_ODDS)
        assert odds_bet.amount == 25  # 5 * 5x on point 6

    def test_replaces_pass_line_after_resolution(self) -> None:
        # Come-out 7 wins, next come-out should place a new pass line.
        table = Table(roller=ScriptedRoller([DiceRoll(3, 4), DiceRoll(3, 3)]))
        results = run_strategy(PassLineWithOdds(), table, max_rolls=2)
        assert results[0].resolutions[0].kind is BetType.PASS_LINE
        assert any(b.kind is BetType.PASS_LINE for b in table.active_bets)

    def test_full_cycle_point_hit(self) -> None:
        # Come-out 6, point phase 4 (no-op), point 6 hit → win.
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(2, 2), DiceRoll(4, 2)]))
        results = run_strategy(PassLineWithOdds(), table, max_rolls=3)
        final = results[2]
        by_kind = {r.kind: r for r in final.resolutions}
        assert by_kind[BetType.PASS_LINE].payout == 5
        assert by_kind[BetType.PASS_ODDS].payout == 30  # 25 * 6/5

    def test_convergence_vs_closed_form(self) -> None:
        table = Table(seed=0xBE77ED)
        strategy = PassLineWithOdds(line_amount=1)
        results = run_strategy(strategy, table, max_rolls=500_000)
        total_payout = sum(r.payout for res in results for r in res.resolutions)
        total_wagered = sum(
            r.amount
            for res in results
            for r in res.resolutions
            if r.kind in (BetType.PASS_LINE, BetType.PASS_ODDS)
        )
        if total_wagered == 0:
            pytest.skip("no wagers placed")
        empirical_edge = -total_payout / total_wagered
        expected_edge = float(pass_line_plus_odds_edge(ODDS_3_4_5X))
        # 5-sigma tolerance on the edge estimate.
        sem = 1.0 / (len(results) ** 0.5)
        assert abs(empirical_edge - expected_edge) < 5 * sem


class TestIronCross:
    """IronCross: pass line + place 5/6/8 + field every roll."""

    def test_places_pass_line_on_come_out(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        run_strategy(IronCross(), table, max_rolls=1)
        assert any(b.kind is BetType.PASS_LINE for b in table.active_bets)

    def test_spreads_iron_cross_on_point_phase(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 5)]))
        results = run_strategy(IronCross(), table, max_rolls=2)
        # After roll 2 (point phase), place bets on 5/6/8 + field resolved.
        place_points = {b.point for b in table.active_bets if b.kind is BetType.PLACE}
        assert place_points == {5, 6, 8}
        # Field resolved on roll 2 (sum 9 = field winner).
        field_res = [r for r in results[1].resolutions if r.kind is BetType.FIELD]
        assert len(field_res) == 1

    def test_field_replaces_every_roll(self) -> None:
        # Two point-phase rolls: field should be placed and resolved both times.
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 5), DiceRoll(2, 2)]))
        results = run_strategy(IronCross(), table, max_rolls=3)
        for res in results[1:]:
            assert any(r.kind is BetType.FIELD for r in res.resolutions)

    def test_does_not_duplicate_place_bets(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 5), DiceRoll(2, 2)]))
        run_strategy(IronCross(), table, max_rolls=3)
        place_bets = [b for b in table.active_bets if b.kind is BetType.PLACE]
        assert len(place_bets) == 3

    def test_seven_out_clears_everything(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 5), DiceRoll(1, 6)]))
        results = run_strategy(IronCross(), table, max_rolls=3)
        # Seven-out on roll 3: all bets lose.
        assert table.active_bets == ()
        assert all(r.payout < 0 for r in results[2].resolutions if r.kind is not BetType.FIELD)
