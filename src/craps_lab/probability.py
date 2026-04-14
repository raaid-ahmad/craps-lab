"""Closed-form probability distributions for the dice in craps.

The fundamental distribution for craps is the sum of two six-sided dice.
This module derives and exposes its probability mass function in closed
form, using exact rational arithmetic so that every downstream analytical
result (house edges, expected loss per roll, variance decompositions) is
computed without introducing floating-point error.

## Derivation

Rolling two fair, independent six-sided dice gives a sample space of
:math:`6 \\times 6 = 36` equally likely ordered pairs ``(d1, d2)``. For
each target sum ``s`` in ``{2, ..., 12}``, the probability ``P(S = s)``
is the number of ordered pairs ``(d1, d2)`` with ``d1 + d2 = s`` and
``1 <= d1, d2 <= 6``, divided by 36.

Counting those pairs gives the classical "tent" distribution::

    s  | count | P(S = s)
    ---|-------|---------
    2  |   1   |  1/36
    3  |   2   |  2/36
    4  |   3   |  3/36
    5  |   4   |  4/36
    6  |   5   |  5/36
    7  |   6   |  6/36   <- mode
    8  |   5   |  5/36
    9  |   4   |  4/36
    10 |   3   |  3/36
    11 |   2   |  2/36
    12 |   1   |  1/36

The count at sum ``s`` can be written compactly as
``min(s - MIN_SUM + 1, MAX_SUM - s + 1)`` for ``s`` in the valid range,
which captures the tent's symmetric growth and decay in one expression.
The expected value ``E[S] = 7`` follows immediately from the symmetry
of the distribution about 7, and ``P(S = 7) = 1/6`` is the single most
important number in craps: it governs every come-out natural, every
7-out, and the long-run "edge" of every bet that resolves against a
seven.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Final

NUM_DICE: Final = 2
MIN_FACE: Final = 1
MAX_FACE: Final = 6

TWO_DICE_SAMPLE_SPACE_SIZE: Final = MAX_FACE**NUM_DICE
"""Total number of ordered ``(d1, d2)`` outcomes for two six-sided dice (36)."""

MIN_TWO_DICE_SUM: Final = NUM_DICE * MIN_FACE
"""Smallest possible sum of two d6 (2)."""

MAX_TWO_DICE_SUM: Final = NUM_DICE * MAX_FACE
"""Largest possible sum of two d6 (12)."""


def two_dice_sum_count(total: int) -> int:
    """Return the number of ``(d1, d2)`` ordered pairs that sum to ``total``.

    Inside the valid range ``[MIN_TWO_DICE_SUM, MAX_TWO_DICE_SUM]`` the
    count follows a symmetric tent centered at 7. It can be written as
    ``min(total - MIN + 1, MAX - total + 1)``, where the first arm is
    the distance from the low end (for ``total <= 7``) and the second
    is the distance from the high end (for ``total >= 7``); they agree
    at the peak with value 6. Outside the valid range the count is zero.
    """
    if not MIN_TWO_DICE_SUM <= total <= MAX_TWO_DICE_SUM:
        return 0
    return min(total - MIN_TWO_DICE_SUM + 1, MAX_TWO_DICE_SUM - total + 1)


def two_dice_sum_pmf() -> dict[int, Fraction]:
    """Return the exact PMF of the sum of two six-sided dice.

    Values are ``fractions.Fraction`` instances so that downstream
    analytic computations (expected values, house edges, variance)
    stay in exact rationals — no floating-point rounding — until the
    final display step.
    """
    return {
        total: Fraction(two_dice_sum_count(total), TWO_DICE_SAMPLE_SPACE_SIZE)
        for total in range(MIN_TWO_DICE_SUM, MAX_TWO_DICE_SUM + 1)
    }
