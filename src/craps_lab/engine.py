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

The module covers the full line-bet family: pass line / come bets
share a resolver (both track their state through their own
``point`` field, not the table point), and so do don't-pass /
don't-come. Take-odds (pass odds, come odds) and lay-odds
(don't-pass odds, don't-come odds) are unified the same way.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from craps_lab.bets import (
    DONT_PASS_BAR,
    DONT_PASS_COME_OUT_LOSES,
    DONT_PASS_COME_OUT_WINS,
    DONT_PASS_LAY_PAYOUT_RATIO,
    PASS_LINE_CRAPS_LOSERS,
    PASS_LINE_NATURAL_WINNERS,
    PASS_ODDS_PAYOUT_RATIO,
    PLACE_PAYOUT_RATIO,
    POINT_NUMBERS,
    SEVEN,
    BetType,
    Outcome,
)
from craps_lab.dice import DiceRoller

if TYPE_CHECKING:
    from craps_lab.dice import DiceRoll
    from craps_lab.play import RollSource


_PASS_FAMILY: frozenset[BetType] = frozenset({BetType.PASS_LINE, BetType.COME})
_DONT_PASS_FAMILY: frozenset[BetType] = frozenset({BetType.DONT_PASS, BetType.DONT_COME})
_TAKE_ODDS_FAMILY: frozenset[BetType] = frozenset({BetType.PASS_ODDS, BetType.COME_ODDS})
_LAY_ODDS_FAMILY: frozenset[BetType] = frozenset({BetType.DONT_PASS_ODDS, BetType.DONT_COME_ODDS})
_LINE_BETS: frozenset[BetType] = frozenset(
    {BetType.PASS_LINE, BetType.DONT_PASS, BetType.COME, BetType.DONT_COME}
)
_COME_OUT_ONLY_LINE_BETS: frozenset[BetType] = frozenset({BetType.PASS_LINE, BetType.DONT_PASS})


def _reject_non_int_field(value: object, name: str) -> None:
    # Exact-type discipline matches :py:class:`craps_lab.dice.DiceRoll`:
    # booleans subclass int and would otherwise sneak through an
    # ``isinstance`` check. For a project whose pitch is rigor, that
    # is exactly the class of bug worth pre-empting at the boundary.
    if type(value) is not int:
        msg = f"{name} must be an int, got {type(value).__name__}"
        raise TypeError(msg)


def _reject_non_positive_field(value: int, name: str) -> None:
    if value < 1:
        msg = f"{name} must be positive, got {value}"
        raise ValueError(msg)


def _validate_wager_amount(kind: BetType, amount: int, point: int) -> None:
    """Reject wagers that would not pay a whole-dollar win.

    Any bet whose payout is computed as ``(amount * numerator) //
    denominator`` must have an ``amount`` that is a multiple of the
    ratio's denominator. This covers free-odds bets (true-odds
    ratios), place bets (sub-true-odds ratios), and any future bet
    kind whose payout is a non-trivial rational multiple of the
    wager.
    """
    if kind in _TAKE_ODDS_FAMILY:
        ratio = PASS_ODDS_PAYOUT_RATIO[point]
    elif kind in _LAY_ODDS_FAMILY:
        ratio = DONT_PASS_LAY_PAYOUT_RATIO[point]
    elif kind is BetType.PLACE:
        ratio = PLACE_PAYOUT_RATIO[point]
    else:
        return
    denom = ratio.denominator
    if amount % denom != 0:
        msg = (
            f"{kind} on point {point} must be a multiple of {denom} "
            f"(payout ratio {ratio.numerator}:{ratio.denominator}); got {amount}"
        )
        raise ValueError(msg)


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

    ``parent_bet_id`` is the ``bet_id`` of the line bet an odds
    wager is attached to, and ``None`` for non-odds bets. The
    engine uses it to enforce at most one odds bet per parent
    (two "pass odds behind the same pass line" is the
    press-your-odds operation, which belongs on a later commit,
    not a silent second :py:class:`ActiveBet`).
    """

    bet_id: int
    kind: BetType
    amount: int
    point: int | None = None
    parent_bet_id: int | None = None

    def __post_init__(self) -> None:
        _reject_non_int_field(self.bet_id, "bet_id")
        _reject_non_positive_field(self.bet_id, "bet_id")
        _reject_non_int_field(self.amount, "amount")
        _reject_non_positive_field(self.amount, "amount")
        if self.point is not None:
            if type(self.point) is not int:
                msg = f"point must be an int or None, got {type(self.point).__name__}"
                raise TypeError(msg)
            if self.point not in POINT_NUMBERS:
                msg = f"point must be one of {POINT_NUMBERS}, got {self.point}"
                raise ValueError(msg)
        if self.parent_bet_id is not None:
            if type(self.parent_bet_id) is not int:
                msg = (
                    f"parent_bet_id must be an int or None, got {type(self.parent_bet_id).__name__}"
                )
                raise TypeError(msg)
            _reject_non_positive_field(self.parent_bet_id, "parent_bet_id")


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

    Carries:

    * the raw :py:class:`DiceRoll`,
    * the table's point before and after this roll (so strategies
      can react to point-set and seven-out transitions without
      having to diff ``table.point`` themselves),
    * :py:attr:`resolutions` — every bet whose state settled (win,
      lose, or push),
    * :py:attr:`travelled` — every bet that *changed its own point*
      on this roll without resolving. A pass-line bet gaining a
      point on the come-out and a come bet travelling to its own
      come point both appear here. Strategies that want to react
      to "my come bet just travelled to 8, place some odds behind
      it" read this list rather than diffing ``active_bets``.

    Bets that stayed on the table unchanged are absent from both
    ``resolutions`` and ``travelled``.
    """

    roll: DiceRoll
    point_before: int | None
    point_after: int | None
    resolutions: tuple[BetResolution, ...]
    travelled: tuple[ActiveBet, ...] = ()


class Table:
    """Craps table state machine.

    Owns a dice source, a point-on / point-off flag, and a list of
    :py:class:`ActiveBet` records. Each call to :py:meth:`roll`
    advances the dice, resolves every active bet against the roll,
    updates the table point, and returns a :py:class:`RollResolution`
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

    def place_bet(
        self,
        kind: BetType,
        amount: int,
        *,
        linked_bet_id: int | None = None,
        number: int | None = None,
    ) -> int:
        """Place a bet of the given kind and amount; return its ``bet_id``.

        Phase and uniqueness validation are enforced here:

        * Pass line / don't pass: come-out phase only, and at most
          one of each kind active at a time. Pressing an existing
          contract is a later feature, not a silent second bet.
        * Come / don't come: point phase only (the table must have
          an established point). Multiple come / don't-come bets
          may be active simultaneously; each tracks its own point.
        * Pass odds / don't-pass odds: point phase, with the
          matching line bet already on the table, and no existing
          odds bet already attached to it. ``linked_bet_id`` is
          auto-resolved — at most one pass-line and one don't-pass
          bet may exist — so passing it explicitly is an error.
        * Come odds / don't-come odds: ``linked_bet_id`` is required,
          must be an exact ``int``, must reference an active come /
          don't-come bet that has established its own point, and
          must not already have an odds bet attached.
        * Place: point phase, ``number`` required (must be a point
          number). At most one place bet per number.
        """
        if type(kind) is not BetType:
            msg = f"kind must be a BetType, got {type(kind).__name__}"
            raise TypeError(msg)
        self._validate_placement(kind, linked_bet_id, number)
        bet_point = self._resolve_bet_point(kind, linked_bet_id, number)
        parent_bet_id = self._resolve_parent_bet_id(kind, linked_bet_id)
        if bet_point is not None:
            _validate_wager_amount(kind, amount, bet_point)
        bet = ActiveBet(
            bet_id=self._next_bet_id,
            kind=kind,
            amount=amount,
            point=bet_point,
            parent_bet_id=parent_bet_id,
        )
        self._next_bet_id += 1
        self._bets.append(bet)
        return bet.bet_id

    def roll(self) -> RollResolution:
        """Roll the dice once and resolve every active bet against it.

        Returns a :py:class:`RollResolution` describing the dice,
        the table's point state before and after the roll, every
        bet whose state settled (``resolutions``), and every bet
        that changed its own point without settling (``travelled``).
        Bets that stayed on the table unchanged appear in neither.
        """
        dice = self._roller.roll()
        total = dice.total
        point_before = self._point

        resolutions: list[BetResolution] = []
        travelled: list[ActiveBet] = []
        carried_over: list[ActiveBet] = []
        for bet in self._bets:
            step = _step_bet(bet, total)
            if isinstance(step, BetResolution):
                resolutions.append(step)
                continue
            carried_over.append(step)
            # Identity comparison works here because the resolvers only
            # return a new ActiveBet via ``replace(bet, point=...)`` when
            # the bet's state changed; a non-resolving roll returns the
            # same object unchanged.
            if step is not bet:
                travelled.append(step)

        self._bets = carried_over
        self._point = _next_point(total, point_before)

        return RollResolution(
            roll=dice,
            point_before=point_before,
            point_after=self._point,
            resolutions=tuple(resolutions),
            travelled=tuple(travelled),
        )

    def _validate_placement(
        self,
        kind: BetType,
        linked_bet_id: int | None,
        number: int | None = None,
    ) -> None:
        if kind in _LINE_BETS:
            self._validate_line_bet(kind, linked_bet_id)
            self._reject_number(kind, number)
            return
        if kind in (BetType.PASS_ODDS, BetType.DONT_PASS_ODDS):
            self._validate_line_odds(kind, linked_bet_id)
            self._reject_number(kind, number)
            return
        if kind is BetType.COME_ODDS:
            self._require_linked_bet_with_point(kind, linked_bet_id, BetType.COME)
            self._reject_number(kind, number)
            return
        if kind is BetType.DONT_COME_ODDS:
            self._require_linked_bet_with_point(kind, linked_bet_id, BetType.DONT_COME)
            self._reject_number(kind, number)
            return
        if kind is BetType.PLACE:
            self._validate_place_bet(linked_bet_id, number)
            return
        msg = f"engine does not yet support placing bet of kind {kind}"
        raise NotImplementedError(msg)

    def _validate_line_bet(self, kind: BetType, linked_bet_id: int | None) -> None:
        self._reject_linked(kind, linked_bet_id)
        if kind in _COME_OUT_ONLY_LINE_BETS:
            self._require_come_out(kind)
            if self._find_any_bet_of_kind(kind) is not None:
                msg = f"a {kind} bet is already active; only one may be placed at a time"
                raise ValueError(msg)
        else:
            self._require_point_phase(kind)

    def _validate_line_odds(self, kind: BetType, linked_bet_id: int | None) -> None:
        self._reject_linked(kind, linked_bet_id)
        self._require_point_phase(kind)
        line_kind = BetType.PASS_LINE if kind is BetType.PASS_ODDS else BetType.DONT_PASS
        line_bet = self._find_line_bet_with_point(line_kind)
        if line_bet is None:
            pretty = "pass line" if line_kind is BetType.PASS_LINE else "dont pass"
            msg = f"{kind} requires an existing {pretty} bet with a point"
            raise ValueError(msg)
        if self._find_odds_bet_for_parent(line_bet.bet_id) is not None:
            msg = f"{kind} is already attached to bet {line_bet.bet_id}"
            raise ValueError(msg)

    def _resolve_bet_point(
        self,
        kind: BetType,
        linked_bet_id: int | None,
        number: int | None = None,
    ) -> int | None:
        if kind is BetType.PLACE:
            return number
        parent = self._resolve_parent_bet(kind, linked_bet_id)
        if parent is None:
            return None
        return parent.point

    def _resolve_parent_bet_id(
        self,
        kind: BetType,
        linked_bet_id: int | None,
    ) -> int | None:
        parent = self._resolve_parent_bet(kind, linked_bet_id)
        return None if parent is None else parent.bet_id

    def _resolve_parent_bet(
        self,
        kind: BetType,
        linked_bet_id: int | None,
    ) -> ActiveBet | None:
        # Pass / don't-pass odds: auto-wired to the unique matching line bet.
        # Come / don't-come odds: wired via linked_bet_id. Everything else
        # is parentless.
        if kind in (BetType.PASS_ODDS, BetType.DONT_PASS_ODDS):
            line_kind = BetType.PASS_LINE if kind is BetType.PASS_ODDS else BetType.DONT_PASS
            line_bet = self._find_line_bet_with_point(line_kind)
            if line_bet is None or line_bet.point is None:
                msg = f"no matching line bet for {kind}; _validate_placement missed this case"
                raise RuntimeError(msg)
            return line_bet
        if kind in (BetType.COME_ODDS, BetType.DONT_COME_ODDS):
            if linked_bet_id is None:
                msg = f"{kind} requires linked_bet_id; _validate_placement missed this case"
                raise RuntimeError(msg)
            linked = self._find_bet_by_id(linked_bet_id)
            if linked is None or linked.point is None:
                msg = f"linked bet {linked_bet_id} missing or has no point"
                raise RuntimeError(msg)
            return linked
        return None

    def _reject_linked(self, kind: BetType, linked_bet_id: int | None) -> None:
        if linked_bet_id is not None:
            msg = f"{kind} does not accept linked_bet_id"
            raise ValueError(msg)

    def _require_come_out(self, kind: BetType) -> None:
        if self._point is not None:
            msg = f"{kind} can only be placed during the come-out phase"
            raise ValueError(msg)

    def _require_point_phase(self, kind: BetType) -> None:
        if self._point is None:
            msg = f"{kind} can only be placed once a point is established"
            raise ValueError(msg)

    def _require_linked_bet_with_point(
        self,
        odds_kind: BetType,
        linked_bet_id: int | None,
        line_kind: BetType,
    ) -> None:
        if linked_bet_id is None:
            msg = f"{odds_kind} requires linked_bet_id"
            raise ValueError(msg)
        # Exact-int check: booleans subclass int, and without this the
        # engine would happily treat ``linked_bet_id=True`` as the
        # integer 1 and attach odds to the wrong bet.
        if type(linked_bet_id) is not int:
            msg = f"linked_bet_id must be an int, got {type(linked_bet_id).__name__}"
            raise TypeError(msg)
        linked = self._find_bet_by_id(linked_bet_id)
        if linked is None:
            msg = f"linked_bet_id {linked_bet_id} does not match any active bet"
            raise ValueError(msg)
        if linked.kind is not line_kind:
            msg = f"{odds_kind} must link to a {line_kind} bet, not {linked.kind}"
            raise ValueError(msg)
        if linked.point is None:
            msg = f"{odds_kind} requires the linked {line_kind} bet to have a point"
            raise ValueError(msg)
        if self._find_odds_bet_for_parent(linked.bet_id) is not None:
            msg = f"{odds_kind} is already attached to bet {linked.bet_id}"
            raise ValueError(msg)

    def _find_line_bet_with_point(self, kind: BetType) -> ActiveBet | None:
        for bet in self._bets:
            if bet.kind is kind and bet.point is not None:
                return bet
        return None

    def _find_any_bet_of_kind(self, kind: BetType) -> ActiveBet | None:
        for bet in self._bets:
            if bet.kind is kind:
                return bet
        return None

    def _find_bet_by_id(self, bet_id: int) -> ActiveBet | None:
        for bet in self._bets:
            if bet.bet_id == bet_id:
                return bet
        return None

    def _find_odds_bet_for_parent(self, parent_bet_id: int) -> ActiveBet | None:
        for bet in self._bets:
            if bet.parent_bet_id == parent_bet_id:
                return bet
        return None

    def _validate_place_bet(self, linked_bet_id: int | None, number: int | None) -> None:
        self._reject_linked(BetType.PLACE, linked_bet_id)
        self._require_point_phase(BetType.PLACE)
        if number is None:
            msg = "place bet requires number"
            raise ValueError(msg)
        if type(number) is not int:
            msg = f"number must be an int, got {type(number).__name__}"
            raise TypeError(msg)
        if number not in POINT_NUMBERS:
            msg = f"number must be one of {POINT_NUMBERS}, got {number}"
            raise ValueError(msg)
        if self._find_place_bet_on_number(number) is not None:
            msg = f"a place bet on {number} is already active"
            raise ValueError(msg)

    def _find_place_bet_on_number(self, number: int) -> ActiveBet | None:
        for bet in self._bets:
            if bet.kind is BetType.PLACE and bet.point == number:
                return bet
        return None

    @staticmethod
    def _reject_number(kind: BetType, number: int | None) -> None:
        if number is not None:
            msg = f"{kind} does not accept number"
            raise ValueError(msg)


def _step_bet(bet: ActiveBet, total: int) -> BetResolution | ActiveBet:
    if bet.kind in _PASS_FAMILY:
        return _step_pass_or_come(bet, total)
    if bet.kind in _DONT_PASS_FAMILY:
        return _step_dont_pass_or_come(bet, total)
    if bet.kind in _TAKE_ODDS_FAMILY:
        return _step_take_odds(bet, total)
    if bet.kind in _LAY_ODDS_FAMILY:
        return _step_lay_odds(bet, total)
    if bet.kind is BetType.PLACE:
        return _step_place(bet, total)
    msg = f"engine cannot yet resolve bet kind {bet.kind}"
    raise NotImplementedError(msg)


def _step_pass_or_come(bet: ActiveBet, total: int) -> BetResolution | ActiveBet:
    # Pass line and come bets share a resolver: both track their state
    # through their own ``point`` field rather than the table point, so
    # a come bet on its own come-out behaves identically to a pass-line
    # bet on the table's come-out. When bet.point is None, the bet is
    # in its own come-out phase; otherwise it is waiting for its point
    # to be hit (win) or for a seven (lose).
    if bet.point is None:
        return _pass_come_out(bet, total)
    return _pass_point_phase(bet, total)


def _pass_come_out(bet: ActiveBet, total: int) -> BetResolution | ActiveBet:
    if total in PASS_LINE_NATURAL_WINNERS:
        return _resolve(bet, Outcome.WIN, bet.amount)
    if total in PASS_LINE_CRAPS_LOSERS:
        return _resolve(bet, Outcome.LOSE, -bet.amount)
    return replace(bet, point=total)


def _pass_point_phase(bet: ActiveBet, total: int) -> BetResolution | ActiveBet:
    if total == SEVEN:
        return _resolve(bet, Outcome.LOSE, -bet.amount)
    if total == bet.point:
        return _resolve(bet, Outcome.WIN, bet.amount)
    return bet


def _step_dont_pass_or_come(bet: ActiveBet, total: int) -> BetResolution | ActiveBet:
    # Mirror of :py:func:`_step_pass_or_come` with the bar-12 push on
    # the bet's own come-out, and inverted wins / losses once the bet
    # has travelled.
    if bet.point is None:
        return _dont_pass_come_out(bet, total)
    return _dont_pass_point_phase(bet, total)


def _dont_pass_come_out(bet: ActiveBet, total: int) -> BetResolution | ActiveBet:
    if total in DONT_PASS_COME_OUT_WINS:
        return _resolve(bet, Outcome.WIN, bet.amount)
    if total in DONT_PASS_COME_OUT_LOSES:
        return _resolve(bet, Outcome.LOSE, -bet.amount)
    if total == DONT_PASS_BAR:
        return _resolve(bet, Outcome.PUSH, 0)
    return replace(bet, point=total)


def _dont_pass_point_phase(bet: ActiveBet, total: int) -> BetResolution | ActiveBet:
    if total == SEVEN:
        return _resolve(bet, Outcome.WIN, bet.amount)
    if total == bet.point:
        return _resolve(bet, Outcome.LOSE, -bet.amount)
    return bet


def _step_take_odds(bet: ActiveBet, total: int) -> BetResolution | ActiveBet:
    if bet.point is None:
        msg = f"take-odds bet {bet.bet_id} has no point; engine invariant violated"
        raise RuntimeError(msg)
    if total == SEVEN:
        return _resolve(bet, Outcome.LOSE, -bet.amount)
    if total == bet.point:
        ratio = PASS_ODDS_PAYOUT_RATIO[bet.point]
        # Exact integer arithmetic: `_validate_wager_amount` rejects any
        # wager that is not a multiple of `ratio.denominator`, so this
        # division has no truncation.
        payout = (bet.amount * ratio.numerator) // ratio.denominator
        return _resolve(bet, Outcome.WIN, payout)
    return bet


def _step_lay_odds(bet: ActiveBet, total: int) -> BetResolution | ActiveBet:
    if bet.point is None:
        msg = f"lay-odds bet {bet.bet_id} has no point; engine invariant violated"
        raise RuntimeError(msg)
    if total == SEVEN:
        ratio = DONT_PASS_LAY_PAYOUT_RATIO[bet.point]
        # Exact integer arithmetic — see :py:func:`_step_take_odds`.
        payout = (bet.amount * ratio.numerator) // ratio.denominator
        return _resolve(bet, Outcome.WIN, payout)
    if total == bet.point:
        return _resolve(bet, Outcome.LOSE, -bet.amount)
    return bet


def _step_place(bet: ActiveBet, total: int) -> BetResolution | ActiveBet:
    if bet.point is None:
        msg = f"place bet {bet.bet_id} has no point; engine invariant violated"
        raise RuntimeError(msg)
    if total == SEVEN:
        return _resolve(bet, Outcome.LOSE, -bet.amount)
    if total == bet.point:
        ratio = PLACE_PAYOUT_RATIO[bet.point]
        payout = (bet.amount * ratio.numerator) // ratio.denominator
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
