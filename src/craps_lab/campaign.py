"""Campaign runner: aggregate many sessions and compare strategies.

A campaign runs one strategy through many independent sessions and
collects the results. :py:func:`compare_strategies` runs several
strategies against identical dice sequences so their outcomes can
be compared fairly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from craps_lab.engine import Table
from craps_lab.session import StopReason, run_session

if TYPE_CHECKING:
    from collections.abc import Sequence

    from craps_lab.session import SessionConfig, SessionResult
    from craps_lab.strategy import Strategy


# ------------------------------------------------------------------
# Validation helpers
# ------------------------------------------------------------------


def _reject_non_int(value: object, name: str) -> None:
    if type(value) is not int:
        msg = f"{name} must be an int, got {type(value).__name__}"
        raise TypeError(msg)


def _reject_non_positive(value: int, name: str) -> None:
    if value < 1:
        msg = f"{name} must be positive, got {value}"
        raise ValueError(msg)


# ------------------------------------------------------------------
# Public types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CampaignResult:
    """Results from running one strategy across many sessions."""

    strategy_name: str
    config: SessionConfig
    sessions: tuple[SessionResult, ...]
    base_seed: int


@dataclass(frozen=True, slots=True)
class CampaignSummary:
    """Aggregate statistics for a campaign."""

    strategy_name: str
    session_count: int
    win_rate: float
    bust_rate: float
    stop_win_rate: float
    stop_loss_rate: float
    time_limit_rate: float
    mean_pnl: float
    median_pnl: float
    std_pnl: float
    percentile_5: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    mean_rolls: float
    mean_peak: float
    mean_trough: float
    mean_drawdown: float


# ------------------------------------------------------------------
# Campaign runners
# ------------------------------------------------------------------


def run_campaign(
    strategy: Strategy,
    config: SessionConfig,
    *,
    sessions: int,
    base_seed: int = 0,
) -> CampaignResult:
    """Run *strategy* for *sessions* independent sessions.

    Each session uses ``Table(seed=base_seed + i)`` so results are
    deterministic and reproducible.

    The same *strategy* instance is reused across sessions. Strategies
    **must be stateless** — all per-roll state should come from the
    :py:class:`~craps_lab.strategy.Context`, not from instance
    attributes that carry over between sessions.
    """
    _reject_non_int(sessions, "sessions")
    _reject_non_positive(sessions, "sessions")
    _reject_non_int(base_seed, "base_seed")

    results: list[SessionResult] = []
    for i in range(sessions):
        table = Table(seed=base_seed + i)
        results.append(run_session(strategy, table, config))

    return CampaignResult(
        strategy_name=strategy.name,
        config=config,
        sessions=tuple(results),
        base_seed=base_seed,
    )


def compare_strategies(
    strategies: Sequence[Strategy],
    config: SessionConfig,
    *,
    sessions: int,
    base_seed: int = 0,
) -> tuple[CampaignResult, ...]:
    """Run each strategy with the same dice sequences for fair comparison.

    Each strategy sees ``Table(seed=base_seed + i)`` for session *i*,
    so every strategy faces the same rolls.
    """
    if not strategies:
        msg = "strategies must be non-empty"
        raise ValueError(msg)
    return tuple(
        run_campaign(s, config, sessions=sessions, base_seed=base_seed) for s in strategies
    )


# ------------------------------------------------------------------
# Summary statistics
# ------------------------------------------------------------------


def summarize(campaign: CampaignResult) -> CampaignSummary:
    """Compute aggregate statistics from a campaign's raw results."""
    results = campaign.sessions
    n = len(results)
    if n == 0:
        msg = "campaign has no sessions"
        raise ValueError(msg)

    nets = np.array([r.net for r in results], dtype=np.float64)
    rolls = np.array([r.rolls for r in results], dtype=np.float64)
    peaks = np.array([r.peak for r in results], dtype=np.float64)
    troughs = np.array([r.trough for r in results], dtype=np.float64)
    drawdowns = np.array([r.max_drawdown for r in results], dtype=np.float64)

    stop_counts = dict.fromkeys(StopReason, 0)
    for r in results:
        stop_counts[r.stop_reason] += 1

    return CampaignSummary(
        strategy_name=campaign.strategy_name,
        session_count=n,
        win_rate=float(np.mean(nets > 0)),
        bust_rate=stop_counts[StopReason.BUST] / n,
        stop_win_rate=stop_counts[StopReason.STOP_WIN] / n,
        stop_loss_rate=stop_counts[StopReason.STOP_LOSS] / n,
        time_limit_rate=stop_counts[StopReason.TIME_LIMIT] / n,
        mean_pnl=float(np.mean(nets)),
        median_pnl=float(np.median(nets)),
        std_pnl=float(np.std(nets, ddof=0)),
        percentile_5=float(np.percentile(nets, 5)),
        percentile_25=float(np.percentile(nets, 25)),
        percentile_75=float(np.percentile(nets, 75)),
        percentile_95=float(np.percentile(nets, 95)),
        mean_rolls=float(np.mean(rolls)),
        mean_peak=float(np.mean(peaks)),
        mean_trough=float(np.mean(troughs)),
        mean_drawdown=float(np.mean(drawdowns)),
    )
