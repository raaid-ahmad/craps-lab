"""Bet types, outcome values, and the rule constants that define them.

This module is the authoritative home for:

* :py:class:`Outcome` — WIN / LOSE / PUSH, the three possible results
  of playing one bet to resolution.
* :py:class:`BetType` — the enumerated bet kinds supported by the
  project. New variants get added here as each phase introduces
  another bet.
* Rule constants that the two sides of the pass / don't-pass line
  disagree about: which come-out sums are immediate wins vs. losses,
  which sum is barred (pushes), which set of sums establishes a point,
  and the special "seven-out" sum.

Keeping rule constants here — rather than in :py:mod:`craps_lab.probability`
— keeps the *rules* of craps separate from the *math* derived over
them. The probability module imports from this one; it never defines
its own rule values.
"""

from __future__ import annotations

from enum import StrEnum
from fractions import Fraction
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping


class Outcome(StrEnum):
    """The result of playing one bet to resolution."""

    WIN = "win"
    LOSE = "lose"
    PUSH = "push"


class BetType(StrEnum):
    """Enumerated bet kinds supported by craps-lab.

    Covers the line-bet family (pass line, don't pass, come, don't
    come) and their associated odds bets. New variants are added as
    subsequent phases introduce more bets.
    """

    PASS_LINE = "pass_line"  # noqa: S105 -- StrEnum value, not a password
    DONT_PASS = "dont_pass"  # noqa: S105 -- StrEnum value, not a password
    COME = "come"
    DONT_COME = "dont_come"
    PASS_ODDS = "pass_odds"  # noqa: S105 -- StrEnum value, not a password
    DONT_PASS_ODDS = "dont_pass_odds"  # noqa: S105 -- StrEnum value, not a password
    COME_ODDS = "come_odds"
    DONT_COME_ODDS = "dont_come_odds"
    PLACE = "place"
    FIELD = "field"


SEVEN: Final = 7
"""The canonical "seven" sum.

It is both the mode of the 2d6 PMF (``P(S = 7) = 1/6``) and the losing
condition for pass-line bets once a point is established. Every later
bet whose loss condition is "roll a 7" references this constant
rather than a bare literal.
"""

POINT_NUMBERS: Final[tuple[int, ...]] = (4, 5, 6, 8, 9, 10)
"""Come-out sums that establish a point instead of resolving the line bet.

Kept as an ordered tuple (not a set) because iteration order matters
for deterministic test output and reproducible notebook tables.
"""

PASS_LINE_NATURAL_WINNERS: Final[frozenset[int]] = frozenset({7, 11})
"""Come-out sums that win the pass line immediately ("naturals")."""

PASS_LINE_CRAPS_LOSERS: Final[frozenset[int]] = frozenset({2, 3, 12})
"""Come-out sums that lose the pass line immediately ("craps")."""

DONT_PASS_COME_OUT_WINS: Final[frozenset[int]] = frozenset({2, 3})
"""Come-out sums that win the don't-pass bet immediately.

Note that 12 is barred (pushes) under the standard casino rule, so
it does not appear here — see :py:data:`DONT_PASS_BAR`.
"""

DONT_PASS_COME_OUT_LOSES: Final[frozenset[int]] = frozenset({7, 11})
"""Come-out sums that lose the don't-pass bet immediately."""

DONT_PASS_BAR: Final = 12
"""The come-out sum that is barred (pushes) on don't pass.

Without this rule, don't pass would have a slight player edge; the
bar-12 convention is what gives the house its ~1.36% edge, and every
analytical derivation of the don't-pass edge references this constant
explicitly rather than hard-coding 12.
"""

PASS_ODDS_PAYOUT_RATIO: Final[Mapping[int, Fraction]] = {
    4: Fraction(2, 1),
    5: Fraction(3, 2),
    6: Fraction(6, 5),
    8: Fraction(6, 5),
    9: Fraction(3, 2),
    10: Fraction(2, 1),
}
"""Payout ratio per $1 pass-odds wager, per point.

Casinos pay "true odds" on pass-line odds bets — the ratio that
exactly compensates the per-point win probability and therefore
produces zero expected value. The values here match
``count(7)/count(p)``: 6/3 = 2/1 for 4 and 10, 6/4 = 3/2 for 5 and
9, and 6/5 for 6 and 8. Laying this ratio is what makes free odds
the one bet on the table with no house edge at all.
"""

DONT_PASS_LAY_PAYOUT_RATIO: Final[Mapping[int, Fraction]] = {
    4: Fraction(1, 2),
    5: Fraction(2, 3),
    6: Fraction(5, 6),
    8: Fraction(5, 6),
    9: Fraction(2, 3),
    10: Fraction(1, 2),
}
"""Payout ratio per $1 don't-pass lay-odds wager, per point.

Lay odds are the inverse of take odds: the player lays more than
they stand to win, reflecting the fact that a don't-pass point
bet is favored to win (the 7 outnumbers every point). The values
here are the reciprocals of :py:data:`PASS_ODDS_PAYOUT_RATIO`, so
a $2 lay on point 4 wins $1 and a $6 lay on point 6 wins $5. The
expected value is exactly zero, identical to take-odds, because
lay and take are two sides of the same fair wager.
"""

PLACE_PAYOUT_RATIO: Final[Mapping[int, Fraction]] = {
    4: Fraction(9, 5),
    5: Fraction(7, 5),
    6: Fraction(7, 6),
    8: Fraction(7, 6),
    9: Fraction(7, 5),
    10: Fraction(9, 5),
}
"""Payout ratio per $1 place-bet wager, per number.

Place bets pay less than true odds — the gap is the house edge.
On point 6 or 8, where true odds are 6:5, the place payout is 7:6
(house edge ~1.52%). On 5 or 9, where true odds are 3:2, the
place payout is 7:5 (house edge 4%). On 4 or 10, where true odds
are 2:1, the place payout is 9:5 (house edge ~6.67%).

The denominator determines the minimum valid wager: place 6/8
must be a multiple of 6, place 5/9/4/10 must be a multiple of 5.
"""

FIELD_WINNERS: Final[frozenset[int]] = frozenset({2, 3, 4, 9, 10, 11, 12})
"""Sums that win the field bet."""

FIELD_LOSERS: Final[frozenset[int]] = frozenset({5, 6, 7, 8})
"""Sums that lose the field bet."""

FIELD_PAYOUT_MULTIPLIER: Final[Mapping[int, int]] = {
    2: 2,
    3: 1,
    4: 1,
    9: 1,
    10: 1,
    11: 1,
    12: 3,
}
"""Payout multiplier per winning field-bet sum.

Most field winners pay 1:1. The 2 pays double (2:1) and the 12
pays triple (3:1) under the standard "double-and-triple" table
rule. Some casinos pay 2:1 on 12 instead — the engine uses the
more common 3:1 variant, which yields a house edge of ~2.78%.
"""
