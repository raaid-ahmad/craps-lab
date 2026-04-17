"""Session runner: bankroll-tracked play sessions with stop conditions.

Where :py:func:`craps_lab.strategy.run_strategy` drives a strategy for
a fixed number of rolls with no financial awareness, this module adds
the bankroll envelope: a starting stake, budget enforcement that skips
bets the player cannot afford, and stop conditions (win target, loss
limit, time limit, bust) that terminate the session early.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from craps_lab.bets import BetType
from craps_lab.strategy import ActionType, Context

if TYPE_CHECKING:
    from collections.abc import Sequence

    from craps_lab.engine import Table
    from craps_lab.strategy import BetAction, Strategy

# Contract bets cannot be taken down when the player leaves the table.
# At session end, these are forfeited (their wager is lost).
_CONTRACT_BETS: frozenset[BetType] = frozenset(
    {
        BetType.PASS_LINE,
        BetType.DONT_PASS,
        BetType.COME,
        BetType.DONT_COME,
    }
)


# ------------------------------------------------------------------
# Validation helpers (same pattern as engine.py, duplicated because
# the engine's versions are module-private).
# ------------------------------------------------------------------


def _reject_non_int(value: object, name: str) -> None:
    if type(value) is not int:
        msg = f"{name} must be an int, got {type(value).__name__}"
        raise TypeError(msg)


def _reject_non_positive(value: int, name: str) -> None:
    if value < 1:
        msg = f"{name} must be positive, got {value}"
        raise ValueError(msg)


# ------------------------------------------------------------------
# Public types
# ------------------------------------------------------------------


class StopReason(StrEnum):
    """Why a session ended."""

    STOP_WIN = "stop_win"
    STOP_LOSS = "stop_loss"
    TIME_LIMIT = "time_limit"
    BUST = "bust"


@dataclass(frozen=True, slots=True)
class SessionConfig:
    """Rules for a single play session.

    ``stop_win`` and ``stop_loss`` are net-profit deltas, not absolute
    bankroll levels. A ``stop_win`` of 200 means "stop when up $200";
    ``stop_loss`` of 300 means "stop when down $300."
    """

    bankroll: int
    max_rolls: int
    stop_win: int | None = None
    stop_loss: int | None = None

    def __post_init__(self) -> None:
        _reject_non_int(self.bankroll, "bankroll")
        _reject_non_positive(self.bankroll, "bankroll")
        _reject_non_int(self.max_rolls, "max_rolls")
        _reject_non_positive(self.max_rolls, "max_rolls")
        if self.stop_win is not None:
            _reject_non_int(self.stop_win, "stop_win")
            _reject_non_positive(self.stop_win, "stop_win")
        if self.stop_loss is not None:
            _reject_non_int(self.stop_loss, "stop_loss")
            _reject_non_positive(self.stop_loss, "stop_loss")


@dataclass(frozen=True, slots=True)
class SessionResult:
    """Summary of a completed play session.

    ``equity_curve`` holds the bankroll after each roll during play.
    ``final_bankroll`` is the walkaway value after forfeiting any
    non-removable contract bets still on the table at session end.
    ``max_drawdown`` is the largest peak-to-subsequent-trough drop
    observed during play (a more accurate risk measure than
    ``initial_bankroll - trough``).
    """

    initial_bankroll: int
    final_bankroll: int
    net: int
    peak: int
    trough: int
    max_drawdown: int
    rolls: int
    stop_reason: StopReason
    equity_curve: tuple[int, ...]


# ------------------------------------------------------------------
# Budget-aware action application
# ------------------------------------------------------------------


def _apply_actions_with_budget(
    table: Table,
    actions: Sequence[BetAction],
    bankroll: int,
) -> None:
    """Apply strategy actions, skipping placements that exceed available funds.

    REMOVE actions always execute. PLACE actions are skipped when
    ``available = bankroll - at_risk < amount``. A ``ValueError``
    from ``table.place_bet`` (e.g., odds behind a skipped line bet)
    is caught and the action is silently skipped.
    """
    for action in actions:
        if action.action is ActionType.REMOVE:
            table.remove_bet(action.bet_id)  # type: ignore[arg-type]
        elif action.action is ActionType.PLACE:
            at_risk = sum(b.amount for b in table.active_bets)
            available = bankroll - at_risk
            if action.amount is None or action.amount > available:
                continue
            try:
                table.place_bet(
                    action.kind,  # type: ignore[arg-type]
                    action.amount,
                    number=action.number,
                    linked_bet_id=action.linked_bet_id,
                )
            except ValueError:
                continue


# ------------------------------------------------------------------
# Session driver
# ------------------------------------------------------------------


def run_session(
    strategy: Strategy,
    table: Table,
    config: SessionConfig,
) -> SessionResult:
    """Run a strategy against a table for one bankroll-tracked session.

    The loop mirrors :py:func:`craps_lab.strategy.run_strategy` but
    adds bankroll tracking, budget enforcement, and early termination
    on stop conditions.
    """
    bankroll = config.bankroll
    initial = config.bankroll
    peak = bankroll
    trough = bankroll
    running_peak = bankroll
    max_drawdown = 0
    equity: list[int] = []
    last_resolution = None
    stop_reason = StopReason.TIME_LIMIT

    for roll_number in range(1, config.max_rolls + 1):
        ctx = Context(
            point=table.point,
            active_bets=table.active_bets,
            last_resolution=last_resolution,
            roll_number=roll_number,
        )
        actions = strategy.get_actions(ctx)
        _apply_actions_with_budget(table, actions, bankroll)

        resolution = table.roll()
        last_resolution = resolution

        bankroll += sum(r.payout for r in resolution.resolutions)
        equity.append(bankroll)
        peak = max(peak, bankroll)
        trough = min(trough, bankroll)
        running_peak = max(running_peak, bankroll)
        max_drawdown = max(max_drawdown, running_peak - bankroll)

        if bankroll <= 0:
            stop_reason = StopReason.BUST
            break
        if config.stop_loss is not None and initial - bankroll >= config.stop_loss:
            stop_reason = StopReason.STOP_LOSS
            break
        if config.stop_win is not None and bankroll - initial >= config.stop_win:
            stop_reason = StopReason.STOP_WIN
            break

    # Forfeit non-removable contract bets still on the table.
    contract_exposure = sum(b.amount for b in table.active_bets if b.kind in _CONTRACT_BETS)
    bankroll -= contract_exposure

    return SessionResult(
        initial_bankroll=initial,
        final_bankroll=bankroll,
        net=bankroll - initial,
        peak=peak,
        trough=trough,
        max_drawdown=max_drawdown,
        rolls=len(equity),
        stop_reason=stop_reason,
        equity_curve=tuple(equity),
    )
