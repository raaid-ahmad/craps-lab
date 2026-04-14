"""Monte Carlo convergence: empirical roller distribution ~ analytical PMF.

This file is the first "analytical vs. simulated" cross-check in the
project: the seeded ``DiceRoller`` should, over many rolls, match the
closed-form PMF computed in ``craps_lab.probability``. Every later
house-edge test will use the same pattern.

## Statistical framing

For ``n`` independent rolls, the count of outcomes equal to sum ``s``
is distributed as ``Binomial(n, p_s)``, where ``p_s`` is the analytical
probability from :py:func:`two_dice_sum_pmf`. Under the null hypothesis
"the roller is faithfully uniform over ``(d1, d2)``":

* expected count is ``n * p_s``,
* standard deviation of the count is ``sqrt(n * p_s * (1 - p_s))``,
* by the CLT (since ``n * p_s >> 1`` for every sum in our range) the
  count is approximately normally distributed.

A 5-sigma band around the expected count contains every outcome with
probability ``1 - erf(5 / sqrt(2)) ~ 5.7e-7``. With 11 sums in play,
a spurious failure is still below ``1e-5``, and the test is seeded —
so in practice the pass/fail outcome is deterministic. The 5-sigma
framing is there to make the test *principled* rather than coincidental:
we can point at the bound and justify it from first principles.

The sample-mean test uses the analytical variance
``Var(d1 + d2) = 2 * Var(d6) = 2 * 35/12 = 35/6``. The ``35/12`` is
``E[X^2] - (E[X])^2 = 91/6 - 49/4``, and the factor of two follows
from independence. Standard error of the mean across ``n`` trials is
therefore ``sqrt(35 / (6n))``.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import TYPE_CHECKING

import pytest

from craps_lab.bets import Outcome
from craps_lab.dice import DiceRoller
from craps_lab.play import (
    play_come_bet,
    play_dont_come_bet,
    play_dont_pass,
    play_pass_line,
)
from craps_lab.probability import (
    MAX_TWO_DICE_SUM,
    MIN_TWO_DICE_SUM,
    dont_pass_house_edge,
    pass_line_house_edge,
    two_dice_sum_pmf,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from fractions import Fraction

    from craps_lab.play import RollSource

_NUM_TRIALS: int = 100_000
_SEED: int = 0xC0FFEE
_TOLERANCE_SIGMA: float = 5.0

_SINGLE_DIE_VARIANCE: float = 35.0 / 12.0  # E[X^2] - (E[X])^2 = 91/6 - 49/4
_TWO_DICE_VARIANCE: float = 2.0 * _SINGLE_DIE_VARIANCE  # by independence
_TWO_DICE_MEAN: float = 7.0


def _roll_and_count(num_trials: int, seed: int) -> Counter[int]:
    roller = DiceRoller(seed=seed)
    counts: Counter[int] = Counter()
    for _ in range(num_trials):
        counts[roller.roll().total] += 1
    return counts


@pytest.fixture(scope="module")
def empirical_counts() -> Counter[int]:
    return _roll_and_count(_NUM_TRIALS, _SEED)


def test_empirical_frequencies_match_pmf(empirical_counts: Mapping[int, int]) -> None:
    pmf = two_dice_sum_pmf()
    for total in range(MIN_TWO_DICE_SUM, MAX_TWO_DICE_SUM + 1):
        probability = float(pmf[total])
        expected = _NUM_TRIALS * probability
        stddev = math.sqrt(_NUM_TRIALS * probability * (1.0 - probability))
        deviation = abs(empirical_counts[total] - expected)
        assert deviation <= _TOLERANCE_SIGMA * stddev, (
            f"sum={total}: empirical={empirical_counts[total]}, "
            f"expected={expected:.1f}, deviation={deviation:.1f} "
            f"> {_TOLERANCE_SIGMA} sigma ({_TOLERANCE_SIGMA * stddev:.1f})"
        )


def test_sample_mean_converges_to_analytical_mean(
    empirical_counts: Mapping[int, int],
) -> None:
    total_sum = sum(total * count for total, count in empirical_counts.items())
    sample_mean = total_sum / _NUM_TRIALS

    sem = math.sqrt(_TWO_DICE_VARIANCE / _NUM_TRIALS)
    assert abs(sample_mean - _TWO_DICE_MEAN) <= _TOLERANCE_SIGMA * sem


# ---------------------------------------------------------------------------
# Line bet convergence: pass line and don't pass
# ---------------------------------------------------------------------------
#
# Each line-bet game resolves to WIN, LOSE, or (don't pass only) PUSH, so the
# per-game P/L is +1, -1, or 0. The empirical house edge over ``n`` games is
#
#     edge_hat = (count_LOSE - count_WIN) / n = -mean(P/L).
#
# Var(P/L) <= 1 (achieved when there are no pushes; slightly less with
# pushes), so SEM of the sample edge is bounded above by ``1 / sqrt(n)``.
# The 5-sigma tolerance below uses that upper bound as a conservative band,
# which keeps the test principled (no hand-tuning) while tolerating the
# small push-induced variance reduction on don't pass.

_NUM_GAMES: int = 200_000
_GAMES_SEED: int = 0xB0BA


def _empirical_edge(
    n_games: int,
    seed: int,
    play_func: Callable[[RollSource], Outcome],
) -> float:
    roller = DiceRoller(seed=seed)
    win = 0
    lose = 0
    for _ in range(n_games):
        outcome = play_func(roller)
        if outcome == Outcome.WIN:
            win += 1
        elif outcome == Outcome.LOSE:
            lose += 1
    return (lose - win) / n_games


@pytest.mark.parametrize(
    ("play_func", "edge_func", "label"),
    [
        (play_pass_line, pass_line_house_edge, "pass_line"),
        (play_dont_pass, dont_pass_house_edge, "dont_pass"),
    ],
)
def test_line_bet_empirical_edge_matches_analytical(
    play_func: Callable[[RollSource], Outcome],
    edge_func: Callable[[], Fraction],
    label: str,
) -> None:
    empirical = _empirical_edge(_NUM_GAMES, _GAMES_SEED, play_func)
    analytical = float(edge_func())

    sem_upper_bound = math.sqrt(1.0 / _NUM_GAMES)
    tolerance = _TOLERANCE_SIGMA * sem_upper_bound

    assert abs(empirical - analytical) <= tolerance, (
        f"{label}: empirical={empirical:.6f}, analytical={analytical:.6f}, "
        f"deviation={abs(empirical - analytical):.6f} > "
        f"{_TOLERANCE_SIGMA} sigma ({tolerance:.6f})"
    )


# ---------------------------------------------------------------------------
# Come bet equivalence: come bets should match line bets byte-for-byte
# ---------------------------------------------------------------------------
#
# ``play_come_bet`` and ``play_dont_come_bet`` delegate to their line-bet
# counterparts, so under the same seed their per-game outcome sequences
# must be *identical* — which means the empirical house edge over n games
# is also identical, not merely within a confidence band. Testing exact
# equality (rather than a 5-sigma band like the line-bet convergence test)
# catches any future delegation drift at the sample level.

_EQUIVALENCE_N_GAMES: int = 10_000


@pytest.mark.parametrize(
    ("come_func", "line_func", "label"),
    [
        (play_come_bet, play_pass_line, "come_vs_pass_line"),
        (play_dont_come_bet, play_dont_pass, "dont_come_vs_dont_pass"),
    ],
)
def test_come_bet_empirical_edge_matches_line_bet_exactly(
    come_func: Callable[[RollSource], Outcome],
    line_func: Callable[[RollSource], Outcome],
    label: str,
) -> None:
    come_empirical = _empirical_edge(_EQUIVALENCE_N_GAMES, _GAMES_SEED, come_func)
    line_empirical = _empirical_edge(_EQUIVALENCE_N_GAMES, _GAMES_SEED, line_func)
    assert come_empirical == line_empirical, (
        f"{label}: come empirical {come_empirical}, line empirical {line_empirical}"
    )
