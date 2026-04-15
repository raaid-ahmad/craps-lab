"""Multi-bet table state machine.

Where :py:mod:`craps_lab.play` runs a single bet to resolution as an
analytical testbed, this module owns the full multi-bet game engine:
a :py:class:`Table` with a point state, a collection of
:py:class:`ActiveBet` records, and per-roll resolution against every
active bet at once.

The module exposes four types:

* :py:class:`ActiveBet` — one immutable record of a bet currently on
  the table, carrying a unique ``bet_id`` so strategies can reference
  it later for press / regress / take-down.
* :py:class:`BetResolution` — the outcome of one bet on one roll,
  with a signed ``payout`` (positive on WIN, negative on LOSE, zero
  on PUSH) that is the net change the bet contributes to the
  player's bankroll.
* :py:class:`RollResolution` — the dice that came up, the point
  before and after, and every bet that changed state on this roll.
* :py:class:`Table` — the state machine itself.

This commit implements pass line + pass odds. Come, don't pass,
don't come, and their odds siblings land in the next commit.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from craps_lab.bets import (
    PASS_LINE_CRAPS_LOSERS,
    PASS_LINE_NATURAL_WINNERS,
    PASS_ODDS_PAYOUT_RATIO,
    POINT_NUMBERS,
    SEVEN,
    BetType,
    Outcome,
)
from craps_lab.dice import DiceRoller

if TYPE_CHECKING:
    from craps_lab.dice import DiceRoll
    from craps_lab.play import RollSource


@dataclass(frozen=True, slots=True)
class ActiveBet:
    """A single bet currently on the table.

    Immutable by design: state transitions (e.g., a come bet
    travelling to its own come point) are expressed by replacing
    the record in the table's collection rather than mutating it.
    The ``bet_id`` is unique within one :py:class:`Table`'s
    lifetime and is assigned by the table on placement.

    ``point`` is ``None`` until the bet has a "home" point — for a
    pass-line bet, that is when the come-out establishes the table
    point; for a come bet, when its first-roll sum establishes a
    come point; for odds bets, set at placement time to the
    underlying line bet's point.
    """

    bet_id: int
    kind: BetType
    amount: int
    point: int | None = None

    def __post_init__(self) -> None:
        # Exact-type discipline matches :py:class:`craps_lab.dice.DiceRoll`:
        # booleans subclass int and would otherwise silently sneak through
        # ``isinstance`` checks, and for a project whose pitch is rigor
        # that is exactly the class of bug worth pre-empting at the boundary.
        if type(self.bet_id) is not int:
            msg = f"bet_id must be an int, got {type(self.bet_id).__name__}"
            raise TypeError(msg)
        if self.bet_id < 1:
            msg = f"bet_id must be positive, got {self.bet_id}"
            raise ValueError(msg)
        if type(self.amount) is not int:
            msg = f"amount must be an int, got {type(self.amount).__name__}"
            raise TypeError(msg)
        if self.amount < 1:
            msg = f"amount must be positive, got {self.amount}"
            raise ValueError(msg)
        if self.point is not None:
            if type(self.point) is not int:
                msg = f"point must be an int or None, got {type(self.point).__name__}"
                raise TypeError(msg)
            if self.point not in POINT_NUMBERS:
                msg = f"point must be one of {POINT_NUMBERS}, got {self.point}"
                raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class BetResolution:
    """What happened to one active bet on one roll.

    ``payout`` is the signed net change to the player's bankroll
    from this resolution:

    * positive on :py:attr:`Outcome.WIN` — a $5 pass-line bet
      winning on a come-out 7 has ``payout = 5`` (1:1),
    * negative on :py:attr:`Outcome.LOSE` — a $5 pass-line bet
      losing on a come-out 2 has ``payout = -5``,
    * zero on :py:attr:`Outcome.PUSH` — e.g., a don't-pass bet
      on a come-out 12 (the barred sum).

    Bets that did not change state on a roll (the dice were
    indifferent to them) do not appear in the parent
    :py:class:`RollResolution` list at all.
    """

    bet_id: int
    kind: BetType
    amount: int
    outcome: Outcome
    payout: int


@dataclass(frozen=True, slots=True)
class RollResolution:
    """Everything that happened on one roll of a :py:class:`Table`.

    Carries the raw :py:class:`DiceRoll`, the table's point before
    and after this roll (so strategies can react to point-set and
    seven-out transitions without having to diff ``table.point``
    themselves), and the list of bets whose state resolved.
    """

    roll: DiceRoll
    point_before: int | None
    point_after: int | None
    resolutions: tuple[BetResolution, ...]


class Table:
    """Craps table state machine.

    Owns a dice source, a point-on / point-off flag, and a list of
    :py:class:`ActiveBet` records. Each call to :py:meth:`roll`
    advances the dice, resolves every active bet against the roll,
    updates the point state, and returns a :py:class:`RollResolution`
    summarising the transition.

    The dice source is either a seeded :py:class:`DiceRoller` built
    internally from ``seed``, or any object satisfying the
    :py:class:`craps_lab.play.RollSource` protocol — tests pass in a
    scripted sequence to deterministically drive every branch of
    the resolution logic.
    """

    def __init__(
        self,
        *,
        seed: int | None = None,
        roller: RollSource | None = None,
    ) -> None:
        if roller is not None and seed is not None:
            msg = "pass either seed or roller, not both"
            raise ValueError(msg)
        self._roller: RollSource = roller if roller is not None else DiceRoller(seed=seed)
        self._point: int | None = None
        self._bets: list[ActiveBet] = []
        self._next_bet_id: int = 1

    @property
    def point(self) -> int | None:
        """The current point, or ``None`` during the come-out phase."""
        return self._point

    @property
    def active_bets(self) -> tuple[ActiveBet, ...]:
        """An immutable snapshot of bets currently on the table."""
        return tuple(self._bets)

    def place_bet(self, kind: BetType, amount: int) -> int:
        """Place a bet of the given kind and amount; return its ``bet_id``.

        Phase validation is enforced here: pass line may only be
        placed during the come-out phase; pass odds only during the
        point phase, and only when the matching pass-line bet is
        already on the table. Other bet kinds raise
        :py:exc:`NotImplementedError` until the following commits
        add them.
        """
        self._validate_placement(kind)
        bet_point = self._bet_point_for(kind)
        bet = ActiveBet(
            bet_id=self._next_bet_id,
            kind=kind,
            amount=amount,
            point=bet_point,
        )
        self._next_bet_id += 1
        self._bets.append(bet)
        return bet.bet_id

    def roll(self) -> RollResolution:
        """Roll the dice once and resolve every active bet against it.

        Returns a :py:class:`RollResolution` describing the dice,
        the point state before and after the roll, and every bet
        whose state settled. Bets that did not resolve (non-
        resolving rolls in the point phase, or come bets awaiting
        their own come-out) stay on the table and do not appear in
        the resolution list — except for pass-line bets that
        *travelled* to their own point on a come-out roll, which
        also stay on the table without a resolution entry.
        """
        dice = self._roller.roll()
        total = dice.total
        point_before = self._point

        resolutions: list[BetResolution] = []
        carried_over: list[ActiveBet] = []
        for bet in self._bets:
            step = _step_bet(bet, total, point_before)
            if isinstance(step, BetResolution):
                resolutions.append(step)
            else:
                carried_over.append(step)

        self._bets = carried_over
        self._point = _next_point(total, point_before)

        return RollResolution(
            roll=dice,
            point_before=point_before,
            point_after=self._point,
            resolutions=tuple(resolutions),
        )

    def _validate_placement(self, kind: BetType) -> None:
        if kind is BetType.PASS_LINE:
            if self._point is not None:
                msg = "pass line can only be placed during the come-out phase"
                raise ValueError(msg)
            return
        if kind is BetType.PASS_ODDS:
            if self._point is None:
                msg = "pass odds can only be placed once a point is established"
                raise ValueError(msg)
            if self._find_pass_line_bet() is None:
                msg = "pass odds requires an existing pass line bet"
                raise ValueError(msg)
            return
        msg = f"engine does not yet support placing bet of kind {kind}"
        raise NotImplementedError(msg)

    def _bet_point_for(self, kind: BetType) -> int | None:
        # Pass-odds inherits the table's current point at placement time.
        # Pass-line starts without a point; it acquires one when the
        # come-out roll lands on a point number.
        if kind is BetType.PASS_ODDS:
            return self._point
        return None

    def _find_pass_line_bet(self) -> ActiveBet | None:
        for bet in self._bets:
            if bet.kind is BetType.PASS_LINE:
                return bet
        return None


def _step_bet(
    bet: ActiveBet,
    total: int,
    point_before: int | None,
) -> BetResolution | ActiveBet:
    if bet.kind is BetType.PASS_LINE:
        return _step_pass_line(bet, total, point_before)
    if bet.kind is BetType.PASS_ODDS:
        return _step_pass_odds(bet, total, point_before)
    msg = f"engine cannot yet resolve bet kind {bet.kind}"
    raise NotImplementedError(msg)


def _step_pass_line(
    bet: ActiveBet,
    total: int,
    point_before: int | None,
) -> BetResolution | ActiveBet:
    if point_before is None:
        # Come-out phase: 7/11 win, 2/3/12 lose, 4-10 travel to their own point.
        if total in PASS_LINE_NATURAL_WINNERS:
            return _resolve(bet, Outcome.WIN, bet.amount)
        if total in PASS_LINE_CRAPS_LOSERS:
            return _resolve(bet, Outcome.LOSE, -bet.amount)
        return replace(bet, point=total)
    # Point phase: resolved by 7 or by the bet's own point being rolled.
    if total == SEVEN:
        return _resolve(bet, Outcome.LOSE, -bet.amount)
    if total == bet.point:
        return _resolve(bet, Outcome.WIN, bet.amount)
    return bet


def _step_pass_odds(
    bet: ActiveBet,
    total: int,
    point_before: int | None,
) -> BetResolution | ActiveBet:
    if point_before is None:
        msg = f"pass odds bet {bet.bet_id} resolving during come-out; engine invariant violated"
        raise RuntimeError(msg)
    if total == SEVEN:
        return _resolve(bet, Outcome.LOSE, -bet.amount)
    if total == point_before:
        # True-odds payout: integer-truncated so the engine never pays the
        # player a fractional chip the casino would not pay at a real table.
        payout = (bet.amount * PASS_ODDS_PAYOUT_RATIO[point_before].numerator) // (
            PASS_ODDS_PAYOUT_RATIO[point_before].denominator
        )
        return _resolve(bet, Outcome.WIN, payout)
    return bet


def _resolve(bet: ActiveBet, outcome: Outcome, payout: int) -> BetResolution:
    return BetResolution(
        bet_id=bet.bet_id,
        kind=bet.kind,
        amount=bet.amount,
        outcome=outcome,
        payout=payout,
    )


def _next_point(total: int, point_before: int | None) -> int | None:
    if point_before is None:
        return total if total in POINT_NUMBERS else None
    if total in (SEVEN, point_before):
        return None
    return point_before
