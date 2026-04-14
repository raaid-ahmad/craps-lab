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
from typing import TYPE_CHECKING, Final

from craps_lab.bets import (
    DONT_PASS_BAR,
    DONT_PASS_COME_OUT_WINS,
    DONT_PASS_LAY_PAYOUT_RATIO,
    PASS_LINE_NATURAL_WINNERS,
    PASS_ODDS_PAYOUT_RATIO,
    POINT_NUMBERS,
    SEVEN,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

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


def probability_point_before_seven(point: int) -> Fraction:
    """Return P(roll ``point`` before rolling 7), given a fresh point-phase roll sequence.

    Derivation: given an established point ``p``, every subsequent roll
    either resolves the state (by hitting ``p`` or by hitting 7) or
    leaves the state unchanged. Rolls that don't resolve are irrelevant
    — they just restart the same geometric process, so they cancel out.
    The conditional distribution over the two *resolving* outcomes is
    ``count(p) : count(7)``, therefore

        P(p before 7) = count(p) / (count(p) + count(7)).

    For the six possible points this gives ``1/3`` for 4 and 10,
    ``2/5`` for 5 and 9, and ``5/11`` for 6 and 8.
    """
    if point not in POINT_NUMBERS:
        msg = f"point must be one of {POINT_NUMBERS}, got {point}"
        raise ValueError(msg)
    point_count = two_dice_sum_count(point)
    seven_count = two_dice_sum_count(SEVEN)
    return Fraction(point_count, point_count + seven_count)


def pass_line_win_probability() -> Fraction:
    """Return the closed-form P(pass line wins) under standard craps rules.

    Pass line resolves in two phases:

    1. **Come-out.** Naturals (7 or 11) win immediately, craps (2, 3,
       or 12) lose immediately, and any other sum ``p`` establishes a
       point.
    2. **Point phase.** The shooter rolls until either ``p`` (win) or
       7 (lose), with per-point probability given by
       :py:func:`probability_point_before_seven`.

    Combining both phases,

        P(win) = sum_{s in {7, 11}} P(S = s)
               + sum_{p in points} P(S = p) * P(p before 7).

    All arithmetic stays in exact ``Fraction`` arithmetic, so the
    result is the canonical ``244/495 ~ 0.4929`` rather than a rounded
    float.
    """
    pmf = two_dice_sum_pmf()
    come_out_win = sum(
        (pmf[s] for s in PASS_LINE_NATURAL_WINNERS),
        start=Fraction(0),
    )
    point_win = sum(
        (pmf[p] * probability_point_before_seven(p) for p in POINT_NUMBERS),
        start=Fraction(0),
    )
    return come_out_win + point_win


def pass_line_house_edge() -> Fraction:
    """Return the closed-form pass line house edge.

    Pass line has no push outcomes, so the expected loss per unit bet
    simplifies to ``P(lose) - P(win) = 1 - 2 * P(win)``. The canonical
    value is ``7/495 ~ 0.01414``, i.e. 1.414%.
    """
    win = pass_line_win_probability()
    return Fraction(1) - 2 * win


def dont_pass_win_probability() -> Fraction:
    """Return the closed-form P(don't pass wins) under the bar-12 rule.

    Don't pass resolves as:

    * come-out 2 or 3: immediate win (``P = 3/36``).
    * come-out 12: push under the bar-12 rule (``P = 1/36``); see
      :py:func:`dont_pass_push_probability`.
    * come-out 7 or 11: immediate loss (``P = 8/36``).
    * come-out 4, 5, 6, 8, 9, or 10: point established. Don't pass
      wins if 7 is rolled before the point, with per-point probability
      ``1 - P(point before 7)``.

    Combining the two phases,

        P(win) = P(S in {2, 3})
               + sum_{p in points} P(S = p) * (1 - P(p before 7)).

    All in exact ``Fraction``; the canonical value is ``949/1980``.
    """
    pmf = two_dice_sum_pmf()
    come_out_win = sum(
        (pmf[s] for s in DONT_PASS_COME_OUT_WINS),
        start=Fraction(0),
    )
    point_win = sum(
        (pmf[p] * (Fraction(1) - probability_point_before_seven(p)) for p in POINT_NUMBERS),
        start=Fraction(0),
    )
    return come_out_win + point_win


def dont_pass_push_probability() -> Fraction:
    """Return ``P(don't pass pushes)``, i.e. ``P(S = 12)`` on the come-out.

    Under standard casino rules, the sum 12 is barred (pushes) on
    don't pass. The value is just ``P(S = 12) = 1/36``.
    """
    return two_dice_sum_pmf()[DONT_PASS_BAR]


def dont_pass_house_edge() -> Fraction:
    """Return the closed-form don't pass house edge (bar 12).

    ``E[P/L] = P(win) * 1 + P(push) * 0 + P(lose) * (-1)``. Under the
    bar-12 rule, ``P(lose) = 1 - P(win) - P(push)``, so

        edge = -E[P/L] = 1 - 2 * P(win) - P(push).

    The canonical value is ``3/220 ~ 0.01364``, i.e. 1.364%. That is
    slightly lower than the pass line's 1.414% because during the
    point phase don't pass pays off against the 7 (count 6) rather
    than against the specific point (count 3, 4, or 5).
    """
    win = dont_pass_win_probability()
    push = dont_pass_push_probability()
    return Fraction(1) - 2 * win - push


def come_bet_win_probability() -> Fraction:
    """Return ``P(come bet wins)``.

    A come bet is placed during the point phase; the *next* roll
    plays the same role as a pass line come-out (7 or 11 win, 2, 3,
    or 12 lose, 4-10 establish the *come point*), and subsequent
    rolls resolve that come point vs. 7 via the same geometric
    process as pass line's.

    The dice have no memory. Whatever table state exists at the
    moment a come bet is placed is irrelevant to its resolution, so
    the game tree *from the bet's point of view* is identical to
    pass line's, and the win probability is exactly ``244/495``.
    This function delegates to :py:func:`pass_line_win_probability`
    to make the equivalence explicit in code as well as in math.
    """
    return pass_line_win_probability()


def come_bet_house_edge() -> Fraction:
    """Return the come bet house edge.

    Equal to :py:func:`pass_line_house_edge` by the no-memory
    argument above: ``7/495 ~ 0.01414``, i.e. 1.414%.
    """
    return pass_line_house_edge()


def dont_come_bet_win_probability() -> Fraction:
    """Return ``P(don't come bet wins)``.

    Same no-memory argument as :py:func:`come_bet_win_probability`:
    a don't-come bet's next roll plays the role of a don't-pass
    come-out, with the same bar-12 rule. Win probability is
    ``949/1980``, identical to don't pass.
    """
    return dont_pass_win_probability()


def dont_come_bet_push_probability() -> Fraction:
    """Return ``P(don't come bet pushes)``.

    Equal to :py:func:`dont_pass_push_probability`: ``1/36``.
    """
    return dont_pass_push_probability()


def dont_come_bet_house_edge() -> Fraction:
    """Return the don't come bet house edge.

    Equal to :py:func:`dont_pass_house_edge`: ``3/220 ~ 0.01364``,
    i.e. 1.364%.
    """
    return dont_pass_house_edge()


def pass_odds_expected_value(point: int) -> Fraction:
    """Return ``E[P/L]`` per $1 pass-odds wager on the given point.

    Pass-odds (also called "take odds") pay the true-odds ratio — the
    payout that exactly compensates the per-point win probability —
    so the expected value is zero by construction. Writing it out:

        E[P/L] = P(p before 7) * payout(p) + (1 - P(p before 7)) * (-1)

    With ``P(p before 7) = count(p) / (count(p) + 6)`` and
    ``payout(p) = 6 / count(p)`` (from
    :py:data:`PASS_ODDS_PAYOUT_RATIO`), the first term equals
    ``6 / (count(p) + 6)`` and the second equals
    ``-6 / (count(p) + 6)``. They cancel exactly, for every point.

    This function computes the expected value symbolically using the
    Fraction payout ratio so the zero is exact, not a rounded float.
    """
    if point not in POINT_NUMBERS:
        msg = f"point must be one of {POINT_NUMBERS}, got {point}"
        raise ValueError(msg)
    p_win = probability_point_before_seven(point)
    payout = PASS_ODDS_PAYOUT_RATIO[point]
    return p_win * payout + (Fraction(1) - p_win) * Fraction(-1)


def dont_pass_lay_odds_expected_value(point: int) -> Fraction:
    """Return ``E[P/L]`` per $1 lay-odds wager on the given point.

    Lay odds pay the inverse of pass-odds: ``count(p) / 6`` per $1
    wagered if 7 comes before the point, and ``-$1`` if the point
    comes first. The win and loss probabilities also swap compared
    to pass odds, so the same cancellation gives zero expected
    value:

        E[P/L] = P(7 before p) * payout(p) + P(p before 7) * (-1)

    With ``P(7 before p) = 6 / (count(p) + 6)`` and
    ``payout(p) = count(p) / 6``, the first term equals
    ``count(p) / (count(p) + 6)``, which cancels the second term
    exactly.

    Lay and take odds are mirror images of the same fair bet —
    neither direction has any edge.
    """
    if point not in POINT_NUMBERS:
        msg = f"point must be one of {POINT_NUMBERS}, got {point}"
        raise ValueError(msg)
    p_lose = probability_point_before_seven(point)
    p_win = Fraction(1) - p_lose
    payout = DONT_PASS_LAY_PAYOUT_RATIO[point]
    return p_win * payout + p_lose * Fraction(-1)


ODDS_3_4_5X: Final[Mapping[int, Fraction]] = {
    4: Fraction(3),
    5: Fraction(4),
    6: Fraction(5),
    8: Fraction(5),
    9: Fraction(4),
    10: Fraction(3),
}
"""The canonical 3-4-5x odds policy.

Allows 3x odds on points 4 and 10, 4x on 5 and 9, and 5x on 6 and 8.
The multipliers are calibrated so that a maximum odds bet always
pays exactly 6 times the line bet on a win, regardless of the point:
3x on a 2:1 payout, 4x on a 3:2 payout, and 5x on a 6:5 payout all
produce the same 6x return. Uniform payout simplifies dealer
calculations and is now the most common max in US casinos.
"""


def uniform_odds_policy(multiplier: int | Fraction) -> Mapping[int, Fraction]:
    """Return an odds policy with the same multiplier for every point.

    Useful for exploring how the composite pass-line edge depends on
    the odds multiplier — at ``1x``, ``2x``, ``3x``, ``5x``, ``10x``,
    and the rare ``100x`` found in a handful of Vegas casinos.
    """
    return dict.fromkeys(POINT_NUMBERS, Fraction(multiplier))


def pass_line_plus_odds_edge(odds_policy: Mapping[int, Fraction]) -> Fraction:
    """Return the composite pass line + odds house edge per unit wagered.

    Pass-line expected loss per round is unchanged at ``7/495`` (free
    odds are zero-EV — see :py:func:`pass_odds_expected_value` — so
    they contribute nothing to the numerator). What changes is the
    *denominator*: the average total amount wagered per round grows
    by the average odds bet,

        E[odds bet] = sum_{p in points} P(S = p) * odds_policy[p],

    to ``1 + E[odds bet]``. The composite edge is therefore

        edge = (7 / 495) / (1 + E[odds bet]).

    For the canonical ``ODDS_3_4_5X`` policy, ``E[odds bet] = 25/9``,
    total wagered is ``34/9``, and the composite edge is
    ``(7/495) / (34/9) = 7/1870 ~ 0.374%`` — the standard "3-4-5x
    odds" number quoted in craps literature.

    This function accepts any policy, not just 3-4-5x, so exploring
    uniform 1x / 2x / 5x / 10x / 100x is a one-line substitution.
    """
    pmf = two_dice_sum_pmf()
    expected_odds_bet = sum(
        (pmf[p] * odds_policy[p] for p in POINT_NUMBERS),
        start=Fraction(0),
    )
    total_wagered = Fraction(1) + expected_odds_bet
    return pass_line_house_edge() / total_wagered


LAY_3_4_5X: Final[Mapping[int, Fraction]] = dict.fromkeys(POINT_NUMBERS, Fraction(6))
"""The canonical don't-pass lay policy equivalent to 3-4-5x take odds.

At the casino floor, a "3-4-5x" maximum on the don't-pass side means
the player can lay enough to *win* 3x on 4/10, 4x on 5/9, and 5x on
6/8 — the same maximum win amounts as a pass-line player would take.
Because the lay payout ratios (1:2, 2:3, 5:6) invert the take-odds
ratios, laying enough to win 3x on point 4 means laying 6, laying
enough to win 4x on point 5 means laying 6, and laying enough to
win 5x on point 6 means laying 6 — so the policy is *uniform* 6x
lay across all six points. Another nice mechanical feature of the
3-4-5x system.
"""


def dont_pass_plus_lay_odds_edge(lay_policy: Mapping[int, Fraction]) -> Fraction:
    """Return the composite don't pass + lay odds house edge per unit wagered.

    Don't-pass expected loss per round is unchanged at ``3/220``
    (lay odds are zero-EV — see
    :py:func:`dont_pass_lay_odds_expected_value` — so they contribute
    nothing to the numerator). The denominator grows by the average
    lay bet,

        E[lay bet] = sum_{p in points} P(S = p) * lay_policy[p],

    to ``1 + E[lay bet]``. The composite edge is therefore

        edge = (3 / 220) / (1 + E[lay bet]).

    For the canonical ``LAY_3_4_5X`` policy (uniform 6x lay),
    ``E[lay bet] = 6 * 24/36 = 4``, total wagered is ``5``, and the
    composite edge is ``(3/220) / 5 = 3/1100 ~ 0.273%``.

    That is *lower* than the pass-line-plus-3-4-5x composite edge
    of ``7/1870 ~ 0.374%``: the don't-pass side becomes more
    edge-efficient under free odds because the lay amounts per
    unit line bet are larger than the take amounts (uniform 6x
    vs. the 25/9 average for 3-4-5x take), which dilutes the
    already-smaller don't-pass numerator more aggressively.
    """
    pmf = two_dice_sum_pmf()
    expected_lay_bet = sum(
        (pmf[p] * lay_policy[p] for p in POINT_NUMBERS),
        start=Fraction(0),
    )
    total_wagered = Fraction(1) + expected_lay_bet
    return dont_pass_house_edge() / total_wagered
