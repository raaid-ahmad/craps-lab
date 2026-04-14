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
from typing import Final


class Outcome(StrEnum):
    """The result of playing one bet to resolution."""

    WIN = "win"
    LOSE = "lose"
    PUSH = "push"


class BetType(StrEnum):
    """Enumerated bet kinds supported by craps-lab.

    New variants are added as subsequent phases introduce more bets;
    for now the project covers the two line bets.
    """

    PASS_LINE = "pass_line"  # noqa: S105 -- StrEnum value, not a password
    DONT_PASS = "dont_pass"  # noqa: S105 -- StrEnum value, not a password
    COME = "come"
    DONT_COME = "dont_come"


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
