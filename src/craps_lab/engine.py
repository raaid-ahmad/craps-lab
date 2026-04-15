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

This commit establishes the surface. Per-bet-kind resolution (pass
line + pass odds, then come / don't-pass / don't-come and their
odds) lands in subsequent commits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from craps_lab.bets import POINT_NUMBERS, BetType, Outcome
from craps_lab.dice import DiceRoller

if TYPE_CHECKING:
    from craps_lab.dice import DiceRoll


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
    themselves), and the list of bets whose state changed.
    """

    roll: DiceRoll
    point_before: int | None
    point_after: int | None
    resolutions: tuple[BetResolution, ...]


class Table:
    """Craps table state machine.

    Owns a seeded :py:class:`DiceRoller`, a point-on / point-off
    flag, and a list of :py:class:`ActiveBet` records. Each call
    to :py:meth:`roll` advances the dice, resolves every active
    bet against the roll, updates the point state, and returns a
    :py:class:`RollResolution` summarising the transition.

    Scaffolding: :py:meth:`roll` advances the dice and returns an
    empty resolution list. Per-bet-kind resolution lands in the
    following commits.
    """

    def __init__(self, *, seed: int | None = None) -> None:
        self._roller: DiceRoller = DiceRoller(seed=seed)
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

    def roll(self) -> RollResolution:
        """Roll the dice once and resolve any active bets.

        Scaffolding: advances the dice and returns a
        :py:class:`RollResolution` with an empty
        :py:attr:`~RollResolution.resolutions` tuple. Resolution
        logic lands in the next commit.
        """
        dice = self._roller.roll()
        point_before = self._point
        return RollResolution(
            roll=dice,
            point_before=point_before,
            point_after=self._point,
            resolutions=(),
        )
