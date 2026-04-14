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

from craps_lab.dice import DiceRoller
from craps_lab.probability import (
    MAX_TWO_DICE_SUM,
    MIN_TWO_DICE_SUM,
    two_dice_sum_pmf,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

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
