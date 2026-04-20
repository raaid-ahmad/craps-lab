"""Transform CampaignResult into chart-ready API responses."""

from __future__ import annotations

import numpy as np
from numpy.random import PCG64, Generator

from craps_lab.campaign import CampaignResult, CampaignSummary, summarize

from .schemas import ChartData, EquityPercentiles, SimulateResponse, SummaryStats


def _build_summary(
    campaign: CampaignResult,
    cs: CampaignSummary,
    display_name: str | None = None,
) -> SummaryStats:
    """Build summary stats including avg_win/avg_loss and p10/p90."""
    nets = np.array([s.net for s in campaign.sessions], dtype=np.float64)
    wins = nets[nets > 0]
    losses = nets[nets < 0]

    return SummaryStats(
        strategy_name=display_name if display_name is not None else cs.strategy_name,
        session_count=cs.session_count,
        win_rate=cs.win_rate,
        bust_rate=cs.bust_rate,
        stop_win_rate=cs.stop_win_rate,
        stop_loss_rate=cs.stop_loss_rate,
        time_limit_rate=cs.time_limit_rate,
        mean_pnl=cs.mean_pnl,
        median_pnl=cs.median_pnl,
        std_pnl=cs.std_pnl,
        percentile_5=cs.percentile_5,
        percentile_10=float(np.percentile(nets, 10)),
        percentile_25=cs.percentile_25,
        percentile_75=cs.percentile_75,
        percentile_90=float(np.percentile(nets, 90)),
        percentile_95=cs.percentile_95,
        mean_rolls=cs.mean_rolls,
        mean_drawdown=cs.mean_drawdown,
        avg_win=float(np.mean(wins)) if len(wins) > 0 else 0.0,
        avg_loss=float(np.mean(losses)) if len(losses) > 0 else 0.0,
    )


def _build_equity_percentiles(campaign: CampaignResult) -> EquityPercentiles:
    """Compute percentile bands across all equity curves."""
    sessions = campaign.sessions
    max_len = max(len(s.equity_curve) for s in sessions)
    initial = sessions[0].initial_bankroll

    # Pad shorter curves with their final value
    matrix = np.full((len(sessions), max_len), np.nan)
    for i, s in enumerate(sessions):
        curve = s.equity_curve
        matrix[i, : len(curve)] = curve
        if len(curve) < max_len:
            matrix[i, len(curve) :] = curve[-1] if curve else initial

    # Downsample to at most 250 points for the chart
    step = max(1, max_len // 250)
    indices = list(range(0, max_len, step))
    if indices and indices[-1] != max_len - 1:
        indices.append(max_len - 1)

    sampled = matrix[:, indices]

    return EquityPercentiles(
        rolls=indices,
        p5=np.percentile(sampled, 5, axis=0).tolist(),
        p25=np.percentile(sampled, 25, axis=0).tolist(),
        p50=np.percentile(sampled, 50, axis=0).tolist(),
        p75=np.percentile(sampled, 75, axis=0).tolist(),
        p95=np.percentile(sampled, 95, axis=0).tolist(),
    )


def _sample_equity_curves(campaign: CampaignResult, n: int = 30, seed: int = 0) -> list[list[int]]:
    """Sample a handful of full equity curves for the spaghetti overlay."""
    sessions = campaign.sessions
    count = min(n, len(sessions))
    if count < len(sessions):
        rng = Generator(PCG64(seed))
        indices = rng.choice(len(sessions), size=count, replace=False)
    else:
        indices = np.arange(count)

    curves: list[list[int]] = []
    for idx in indices:
        s = sessions[int(idx)]
        curves.append([s.initial_bankroll, *s.equity_curve])
    return curves


def serialize_campaign(
    campaign: CampaignResult,
    *,
    display_name: str | None = None,
    seed: int = 0,
) -> SimulateResponse:
    """Convert a CampaignResult into a SimulateResponse.

    ``display_name`` overrides the campaign's strategy_name so the
    UI can show a presentation-friendly label (e.g. "Pass Line with
    Odds") instead of the engine's class-name default. ``seed`` is
    echoed back to the client and feeds the equity-curve sampler so a
    reproducible run reproduces the same spaghetti overlay too.
    """
    cs = summarize(campaign)
    return SimulateResponse(
        summary=_build_summary(campaign, cs, display_name=display_name),
        charts=ChartData(
            pnl_values=[s.net for s in campaign.sessions],
            drawdown_values=[s.max_drawdown for s in campaign.sessions],
            equity_percentiles=_build_equity_percentiles(campaign),
            equity_sample=_sample_equity_curves(campaign, seed=seed),
        ),
        seed=seed,
    )
