"""Strategy layer: define a betting strategy and run it against a table.

A :py:class:`Strategy` receives a :py:class:`Context` snapshot before
each roll and returns a sequence of :py:class:`BetAction` objects —
bets to place or take down. The :py:func:`run_strategy` function ties
a strategy to a :py:class:`~craps_lab.engine.Table` for a fixed number
of rolls and returns the full roll-by-roll history.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from craps_lab.bets import BetType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from craps_lab.engine import ActiveBet, RollResolution, Table


class ActionType(StrEnum):
    """Whether a :py:class:`BetAction` places or removes a bet."""

    PLACE = "place"
    REMOVE = "remove"


@dataclass(frozen=True, slots=True)
class BetAction:
    """One action a strategy wants to take before a roll.

    Use the :py:meth:`place` and :py:meth:`remove` factory methods
    rather than constructing directly — they enforce the correct
    field combinations for each action type.
    """

    action: ActionType
    kind: BetType | None = None
    amount: int | None = None
    number: int | None = None
    linked_bet_id: int | None = None
    bet_id: int | None = None

    def __post_init__(self) -> None:
        if self.action is ActionType.PLACE:
            if self.kind is None:
                msg = "PLACE action requires kind"
                raise ValueError(msg)
            if self.amount is None:
                msg = "PLACE action requires amount"
                raise ValueError(msg)
            if self.bet_id is not None:
                msg = "PLACE action does not accept bet_id"
                raise ValueError(msg)
        elif self.action is ActionType.REMOVE:
            if self.bet_id is None:
                msg = "REMOVE action requires bet_id"
                raise ValueError(msg)
            if self.kind is not None:
                msg = "REMOVE action does not accept kind"
                raise ValueError(msg)
            if self.amount is not None:
                msg = "REMOVE action does not accept amount"
                raise ValueError(msg)

    @staticmethod
    def place(
        kind: BetType,
        amount: int,
        *,
        number: int | None = None,
        linked_bet_id: int | None = None,
    ) -> BetAction:
        """Create an action to place a bet."""
        return BetAction(
            action=ActionType.PLACE,
            kind=kind,
            amount=amount,
            number=number,
            linked_bet_id=linked_bet_id,
        )

    @staticmethod
    def remove(bet_id: int) -> BetAction:
        """Create an action to take down (remove) a bet."""
        return BetAction(action=ActionType.REMOVE, bet_id=bet_id)


@dataclass(frozen=True, slots=True)
class Context:
    """What the strategy sees before each roll.

    ``last_resolution`` is ``None`` on the first call (before any
    dice have been rolled). On every subsequent call it carries the
    result of the preceding roll, including ``resolutions`` and
    ``travelled`` so the strategy can react to what happened.
    """

    point: int | None
    active_bets: tuple[ActiveBet, ...]
    last_resolution: RollResolution | None
    roll_number: int


class Strategy(ABC):
    """Base class for betting strategies.

    Subclass and implement :py:meth:`get_actions`. The runner calls
    it once before every roll with a :py:class:`Context` snapshot.
    """

    @abstractmethod
    def get_actions(self, ctx: Context) -> Sequence[BetAction]:
        """Return actions to execute before the next roll."""
        ...

    @property
    def name(self) -> str:
        """Human-readable name; defaults to the class name."""
        return type(self).__name__


_DEFAULT_3_4_5X: dict[int, int] = {4: 3, 5: 4, 6: 5, 8: 5, 9: 4, 10: 3}


class PassLineWithOdds(Strategy):
    """Pass line with odds behind it.

    Come-out: place a pass-line bet. Once the point is established,
    place pass-odds at the configured multiplier (default 3-4-5x).
    """

    def __init__(
        self,
        line_amount: int = 5,
        odds_multiplier: dict[int, int] | None = None,
    ) -> None:
        self._line = line_amount
        self._odds = odds_multiplier or _DEFAULT_3_4_5X

    def get_actions(self, ctx: Context) -> Sequence[BetAction]:
        actions: list[BetAction] = []
        has_pass = any(b.kind is BetType.PASS_LINE for b in ctx.active_bets)
        has_odds = any(b.kind is BetType.PASS_ODDS for b in ctx.active_bets)

        if ctx.point is None and not has_pass:
            actions.append(BetAction.place(BetType.PASS_LINE, self._line))
        if ctx.point is not None and has_pass and not has_odds:
            actions.append(BetAction.place(BetType.PASS_ODDS, self._line * self._odds[ctx.point]))
        return actions


def run_strategy(
    strategy: Strategy,
    table: Table,
    *,
    max_rolls: int,
) -> list[RollResolution]:
    """Drive a strategy against a table for up to ``max_rolls`` rolls."""
    results: list[RollResolution] = []
    for roll_number in range(1, max_rolls + 1):
        ctx = Context(
            point=table.point,
            active_bets=table.active_bets,
            last_resolution=results[-1] if results else None,
            roll_number=roll_number,
        )
        actions = strategy.get_actions(ctx)
        _apply_actions(table, actions)
        results.append(table.roll())
    return results


def _apply_actions(table: Table, actions: Sequence[BetAction]) -> None:
    for action in actions:
        if action.action is ActionType.PLACE:
            # __post_init__ guarantees kind and amount are set for PLACE.
            table.place_bet(
                action.kind,  # type: ignore[arg-type]
                action.amount,  # type: ignore[arg-type]
                number=action.number,
                linked_bet_id=action.linked_bet_id,
            )
        elif action.action is ActionType.REMOVE:
            # __post_init__ guarantees bet_id is set for REMOVE.
            table.remove_bet(action.bet_id)  # type: ignore[arg-type]
