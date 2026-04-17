"""Tests for the session runner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from craps_lab.bets import BetType
from craps_lab.dice import DiceRoll
from craps_lab.engine import Table
from craps_lab.session import SessionConfig, SessionResult, StopReason, run_session
from craps_lab.strategy import BetAction, Context, IronCross, PassLineWithOdds, Strategy

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


class ScriptedRoller:
    def __init__(self, rolls: Iterable[DiceRoll]) -> None:
        self._rolls = iter(rolls)

    def roll(self) -> DiceRoll:
        return next(self._rolls)


class AlwaysPass(Strategy):
    """Place a pass-line bet on every come-out."""

    def __init__(self, amount: int = 5) -> None:
        self._amount = amount

    def get_actions(self, ctx: Context) -> Sequence[BetAction]:
        has_pass = any(b.kind is BetType.PASS_LINE for b in ctx.active_bets)
        if ctx.point is None and not has_pass:
            return [BetAction.place(BetType.PASS_LINE, self._amount)]
        return []


class NeverBet(Strategy):
    """Never place any bets."""

    def get_actions(self, _ctx: Context) -> Sequence[BetAction]:
        return []


# ------------------------------------------------------------------
# SessionConfig validation
# ------------------------------------------------------------------


class TestSessionConfig:
    """Construction and validation of SessionConfig."""

    def test_minimal_construction(self) -> None:
        cfg = SessionConfig(bankroll=500, max_rolls=100)
        assert cfg.bankroll == 500
        assert cfg.max_rolls == 100
        assert cfg.stop_win is None
        assert cfg.stop_loss is None

    def test_full_construction(self) -> None:
        cfg = SessionConfig(bankroll=500, max_rolls=240, stop_win=200, stop_loss=300)
        assert cfg.stop_win == 200
        assert cfg.stop_loss == 300

    def test_is_frozen(self) -> None:
        cfg = SessionConfig(bankroll=500, max_rolls=100)
        with pytest.raises(AttributeError):
            cfg.bankroll = 1000  # type: ignore[misc]

    @pytest.mark.parametrize("bad", [True, 1.0, "500"])
    def test_rejects_non_int_bankroll(self, bad: object) -> None:
        with pytest.raises(TypeError, match="bankroll must be an int"):
            SessionConfig(bankroll=bad, max_rolls=100)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [0, -1])
    def test_rejects_non_positive_bankroll(self, bad: int) -> None:
        with pytest.raises(ValueError, match="bankroll must be positive"):
            SessionConfig(bankroll=bad, max_rolls=100)

    @pytest.mark.parametrize("bad", [True, 1.0, "100"])
    def test_rejects_non_int_max_rolls(self, bad: object) -> None:
        with pytest.raises(TypeError, match="max_rolls must be an int"):
            SessionConfig(bankroll=500, max_rolls=bad)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [0, -1])
    def test_rejects_non_positive_max_rolls(self, bad: int) -> None:
        with pytest.raises(ValueError, match="max_rolls must be positive"):
            SessionConfig(bankroll=500, max_rolls=bad)

    @pytest.mark.parametrize("bad", [True, 1.0, "50"])
    def test_rejects_non_int_stop_win(self, bad: object) -> None:
        with pytest.raises(TypeError, match="stop_win must be an int"):
            SessionConfig(bankroll=500, max_rolls=100, stop_win=bad)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [0, -1])
    def test_rejects_non_positive_stop_win(self, bad: int) -> None:
        with pytest.raises(ValueError, match="stop_win must be positive"):
            SessionConfig(bankroll=500, max_rolls=100, stop_win=bad)

    @pytest.mark.parametrize("bad", [True, 1.0, "50"])
    def test_rejects_non_int_stop_loss(self, bad: object) -> None:
        with pytest.raises(TypeError, match="stop_loss must be an int"):
            SessionConfig(bankroll=500, max_rolls=100, stop_loss=bad)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [0, -1])
    def test_rejects_non_positive_stop_loss(self, bad: int) -> None:
        with pytest.raises(ValueError, match="stop_loss must be positive"):
            SessionConfig(bankroll=500, max_rolls=100, stop_loss=bad)


# ------------------------------------------------------------------
# SessionResult shape
# ------------------------------------------------------------------


class TestSessionResult:
    """SessionResult is a frozen summary."""

    def test_construction(self) -> None:
        r = SessionResult(
            initial_bankroll=100,
            final_bankroll=105,
            net=5,
            peak=110,
            trough=95,
            max_drawdown=15,
            rolls=10,
            stop_reason=StopReason.TIME_LIMIT,
            equity_curve=(100, 105, 95, 110, 105, 100, 95, 100, 105, 105),
        )
        assert r.net == 5
        assert r.stop_reason is StopReason.TIME_LIMIT
        assert r.max_drawdown == 15

    def test_is_frozen(self) -> None:
        r = SessionResult(
            initial_bankroll=100,
            final_bankroll=100,
            net=0,
            peak=100,
            trough=100,
            max_drawdown=0,
            rolls=1,
            stop_reason=StopReason.TIME_LIMIT,
            equity_curve=(100,),
        )
        with pytest.raises(AttributeError):
            r.net = 10  # type: ignore[misc]


# ------------------------------------------------------------------
# Stop reasons
# ------------------------------------------------------------------


class TestStopReasonTimeLimit:
    """Session runs to max_rolls when no stop condition fires."""

    def test_completes_all_rolls(self) -> None:
        # Three come-out 7s — each wins $5 pass line.
        roller = ScriptedRoller([DiceRoll(3, 4)] * 3)
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=100, max_rolls=3)
        result = run_session(AlwaysPass(), table, cfg)

        assert result.stop_reason is StopReason.TIME_LIMIT
        assert result.rolls == 3
        assert len(result.equity_curve) == 3
        assert result.final_bankroll == 115
        assert result.net == 15


class TestStopReasonStopWin:
    """Session stops when net profit reaches stop_win."""

    def test_stops_on_win_threshold(self) -> None:
        # Come-out 7 wins $5, hitting stop_win immediately.
        roller = ScriptedRoller([DiceRoll(3, 4)] * 10)
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=100, max_rolls=100, stop_win=5)
        result = run_session(AlwaysPass(), table, cfg)

        assert result.stop_reason is StopReason.STOP_WIN
        assert result.rolls == 1
        assert result.final_bankroll == 105
        assert result.net == 5

    def test_exact_boundary_triggers(self) -> None:
        # Verify >= (not >) comparison.
        roller = ScriptedRoller([DiceRoll(3, 4)] * 10)
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=100, max_rolls=100, stop_win=5)
        result = run_session(AlwaysPass(), table, cfg)

        assert result.stop_reason is StopReason.STOP_WIN


class TestStopReasonStopLoss:
    """Session stops when net loss reaches stop_loss."""

    def test_stops_on_loss_threshold(self) -> None:
        # Come-out 2 (craps) loses $5, hitting stop_loss immediately.
        roller = ScriptedRoller([DiceRoll(1, 1)] * 10)
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=100, max_rolls=100, stop_loss=5)
        result = run_session(AlwaysPass(), table, cfg)

        assert result.stop_reason is StopReason.STOP_LOSS
        assert result.rolls == 1
        assert result.final_bankroll == 95
        assert result.net == -5

    def test_exact_boundary_triggers(self) -> None:
        roller = ScriptedRoller([DiceRoll(1, 1)] * 10)
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=100, max_rolls=100, stop_loss=5)
        result = run_session(AlwaysPass(), table, cfg)

        assert result.stop_reason is StopReason.STOP_LOSS


class TestStopReasonBust:
    """Session stops when bankroll hits zero."""

    def test_bust_on_bankroll_depletion(self) -> None:
        # Two come-out craps deplete a $10 bankroll.
        roller = ScriptedRoller([DiceRoll(1, 1)] * 10)
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=10, max_rolls=100)
        result = run_session(AlwaysPass(), table, cfg)

        assert result.stop_reason is StopReason.BUST
        assert result.rolls == 2
        assert result.final_bankroll == 0
        assert result.net == -10

    def test_bust_exactly_zero(self) -> None:
        # $5 bankroll, $5 bet, one loss → exactly 0.
        roller = ScriptedRoller([DiceRoll(1, 1)] * 10)
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=5, max_rolls=100)
        result = run_session(AlwaysPass(), table, cfg)

        assert result.stop_reason is StopReason.BUST
        assert result.final_bankroll == 0
        assert result.rolls == 1

    def test_bust_takes_priority_over_stop_loss(self) -> None:
        # bankroll=5, stop_loss=5: both BUST and STOP_LOSS trigger.
        roller = ScriptedRoller([DiceRoll(1, 1)] * 10)
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=5, max_rolls=100, stop_loss=5)
        result = run_session(AlwaysPass(), table, cfg)

        assert result.stop_reason is StopReason.BUST


# ------------------------------------------------------------------
# Budget enforcement
# ------------------------------------------------------------------


class TestBudgetEnforcement:
    """Budget enforcement skips unaffordable bets without crashing."""

    def test_skips_expensive_bet(self) -> None:
        # Strategy wants $100 pass line, bankroll is only $50.
        roller = ScriptedRoller([DiceRoll(3, 4)] * 3)
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=50, max_rolls=3)
        result = run_session(AlwaysPass(amount=100), table, cfg)

        assert result.stop_reason is StopReason.TIME_LIMIT
        assert result.net == 0
        assert result.equity_curve == (50, 50, 50)

    def test_odds_skipped_when_budget_tight(self) -> None:
        # bankroll=8: pass-line ($5) affordable, odds ($25 on 6) not.
        roller = ScriptedRoller(
            [
                DiceRoll(3, 3),  # 6 — establishes point
                DiceRoll(2, 2),  # 4 — neutral (not 6, not 7)
            ]
        )
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=8, max_rolls=2)
        result = run_session(PassLineWithOdds(), table, cfg)

        # Pass line placed, odds skipped.
        assert any(b.kind is BetType.PASS_LINE for b in table.active_bets)
        assert not any(b.kind is BetType.PASS_ODDS for b in table.active_bets)
        # Pass line ($5) forfeited at session end as a contract bet.
        assert result.net == -5

    def test_catches_invalid_placement_gracefully(self) -> None:
        """ValueError from table.place_bet is caught and skipped."""

        class ForceOddsWithoutLine(Strategy):
            """Attempt pass-odds on come-out with no pass-line."""

            def get_actions(self, ctx: Context) -> Sequence[BetAction]:
                if ctx.point is None:
                    return [BetAction.place(BetType.PASS_ODDS, 25)]
                return []

        roller = ScriptedRoller([DiceRoll(3, 4)] * 3)
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=100, max_rolls=3)
        result = run_session(ForceOddsWithoutLine(), table, cfg)

        assert result.stop_reason is StopReason.TIME_LIMIT
        assert result.net == 0
        assert result.rolls == 3

    def test_multi_bet_budget_limits_placements(self) -> None:
        # IronCross with bankroll=20: pass-line + place 5 + place 6
        # fit; place 8 and field do not.
        roller = ScriptedRoller(
            [
                DiceRoll(2, 2),  # 4 — establishes point
                DiceRoll(1, 2),  # 3 — neutral for all active bets
            ]
        )
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=20, max_rolls=2)
        result = run_session(IronCross(), table, cfg)

        kinds = [(b.kind, b.point) for b in table.active_bets]
        assert (BetType.PASS_LINE, 4) in kinds
        assert (BetType.PLACE, 5) in kinds
        assert (BetType.PLACE, 6) in kinds
        assert not any(b.kind is BetType.PLACE and b.point == 8 for b in table.active_bets)
        assert not any(b.kind is BetType.FIELD for b in table.active_bets)
        # Pass line ($5) forfeited at session end; place bets returned.
        assert result.net == -5


# ------------------------------------------------------------------
# Equity curve and result correctness
# ------------------------------------------------------------------


class TestEquityCurve:
    """Equity curve tracks bankroll after each roll."""

    def test_step_by_step_correctness(self) -> None:
        # Win (+5), lose (-5), win (+5).
        roller = ScriptedRoller(
            [
                DiceRoll(3, 4),  # 7 — natural winner
                DiceRoll(1, 1),  # 2 — craps loser
                DiceRoll(3, 4),  # 7 — natural winner
            ]
        )
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=100, max_rolls=3)
        result = run_session(AlwaysPass(), table, cfg)

        assert result.equity_curve == (105, 100, 105)
        assert result.final_bankroll == 105
        assert result.net == 5

    def test_peak_and_trough(self) -> None:
        # Lose (-5), win (+5), win (+5).
        roller = ScriptedRoller(
            [
                DiceRoll(1, 1),  # craps — lose
                DiceRoll(3, 4),  # 7 — win
                DiceRoll(3, 4),  # 7 — win
            ]
        )
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=100, max_rolls=3)
        result = run_session(AlwaysPass(), table, cfg)

        assert result.trough == 95  # after roll 1
        assert result.peak == 105  # after roll 3

    def test_no_bets_means_flat_curve(self) -> None:
        roller = ScriptedRoller([DiceRoll(3, 4)] * 3)
        table = Table(roller=roller)
        cfg = SessionConfig(bankroll=100, max_rolls=3)
        result = run_session(NeverBet(), table, cfg)

        assert result.equity_curve == (100, 100, 100)
        assert result.net == 0
        assert result.stop_reason is StopReason.TIME_LIMIT

    def test_determinism_with_same_seed(self) -> None:
        cfg = SessionConfig(bankroll=500, max_rolls=100)
        r1 = run_session(PassLineWithOdds(), Table(seed=42), cfg)
        r2 = run_session(PassLineWithOdds(), Table(seed=42), cfg)

        assert r1.equity_curve == r2.equity_curve
        assert r1.stop_reason == r2.stop_reason
        assert r1.final_bankroll == r2.final_bankroll
        assert r1.rolls == r2.rolls
