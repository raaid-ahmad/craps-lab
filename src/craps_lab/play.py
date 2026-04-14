"""One-shot "play to resolution" helpers for line bets.

These are the simplest bet runners: drive a roll source forward until
the bet resolves, then return the :py:class:`Outcome`. They exist for
Monte Carlo convergence testing and notebook exploration; a full
state-machine-driven game engine lands in a later phase.

Each runner takes a :py:class:`RollSource` — a structural-typing
Protocol that requires only a ``roll() -> DiceRoll`` method — so
tests can feed in scripted sequences while production code passes
a :py:class:`craps_lab.dice.DiceRoller`. Seeding the roller on the
caller's side makes every play reproducible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from craps_lab.bets import (
    DONT_PASS_BAR,
    DONT_PASS_COME_OUT_LOSES,
    DONT_PASS_COME_OUT_WINS,
    PASS_LINE_CRAPS_LOSERS,
    PASS_LINE_NATURAL_WINNERS,
    SEVEN,
    Outcome,
)

if TYPE_CHECKING:
    from craps_lab.dice import DiceRoll


class RollSource(Protocol):
    """Anything that produces a :py:class:`DiceRoll` on demand.

    This is the minimal interface the play runners need: a single
    ``roll()`` method. The concrete :py:class:`craps_lab.dice.DiceRoller`
    satisfies it by construction, and tests can satisfy it with a
    scripted sequence to deterministically drive every branch of the
    resolution logic.
    """

    def roll(self) -> DiceRoll: ...


def play_pass_line(roller: RollSource) -> Outcome:
    """Play one pass line bet to resolution.

    Consumes one or more rolls until the bet wins or loses. The
    shortest possible play is a single come-out roll (naturals or
    craps); the longest is unbounded in theory but almost surely
    finite in practice — every non-resolving roll leaves the state
    unchanged, and both resolving events have positive probability
    on every draw.
    """
    come_out = roller.roll().total
    if come_out in PASS_LINE_NATURAL_WINNERS:
        return Outcome.WIN
    if come_out in PASS_LINE_CRAPS_LOSERS:
        return Outcome.LOSE
    point = come_out
    while True:
        roll = roller.roll().total
        if roll == SEVEN:
            return Outcome.LOSE
        if roll == point:
            return Outcome.WIN


def play_dont_pass(roller: RollSource) -> Outcome:
    """Play one don't pass (bar 12) bet to resolution.

    Structurally identical to :py:func:`play_pass_line` with two
    differences: the come-out rules are flipped (2 and 3 win, 7 and
    11 lose), and the come-out 12 pushes rather than losing — the
    "bar 12" rule that preserves the house edge on this bet.
    """
    come_out = roller.roll().total
    if come_out in DONT_PASS_COME_OUT_WINS:
        return Outcome.WIN
    if come_out in DONT_PASS_COME_OUT_LOSES:
        return Outcome.LOSE
    if come_out == DONT_PASS_BAR:
        return Outcome.PUSH
    point = come_out
    while True:
        roll = roller.roll().total
        if roll == SEVEN:
            return Outcome.WIN
        if roll == point:
            return Outcome.LOSE


def play_come_bet(roller: RollSource) -> Outcome:
    """Play one come bet to resolution.

    A come bet is placed during the table's point phase and its
    next roll plays the role of a pass line come-out — 7 or 11 wins,
    2/3/12 loses, 4-10 establishes the *come point*, which is then
    resolved vs. 7 by the same geometric process as pass line's.

    From the bet's own perspective the game tree is *identical* to
    pass line's (the dice have no memory), so this runner delegates
    directly to :py:func:`play_pass_line`. The distinction between
    "pass line" and "come bet" only matters at the session level,
    where multiple come bets can be active simultaneously and share
    a seven-out; that bookkeeping belongs to the game engine in a
    later phase, not to a one-shot play runner.
    """
    return play_pass_line(roller)


def play_dont_come_bet(roller: RollSource) -> Outcome:
    """Play one don't come bet to resolution.

    Mirror image of :py:func:`play_come_bet` with the bar-12 rule,
    and — for the same no-memory reason — semantically equivalent
    to :py:func:`play_dont_pass`. Delegates to it directly.
    """
    return play_dont_pass(roller)
