"""Chart functions for campaign visualisation.

Each function accepts a :py:class:`~craps_lab.campaign.CampaignResult`
(or a sequence of them) and returns a :py:class:`matplotlib.figure.Figure`.
The caller decides whether to display, save, or embed the figure.

Requires the ``viz`` optional extra::

    pip install craps-lab[viz]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import matplotlib as mpl

    mpl.use("Agg")
    import matplotlib.pyplot as plt
except ImportError as _err:
    msg = "matplotlib is required for chart functions. Install with: pip install craps-lab[viz]"
    raise ImportError(msg) from _err

import numpy as np
from numpy.random import PCG64, Generator

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

    from craps_lab.campaign import CampaignResult

_PALETTE = ("#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c")


def plot_pnl_histogram(
    campaign: CampaignResult,
    *,
    bins: int = 50,
) -> Figure:
    """Histogram of net P&L across all sessions."""
    nets = [s.net for s in campaign.sessions]
    fig, ax = plt.subplots(tight_layout=True)
    ax.hist(nets, bins=bins, edgecolor="black", linewidth=0.5, alpha=0.7, color=_PALETTE[0])
    ax.axvline(0, color=_PALETTE[1], linestyle="--", linewidth=1, label="Break-even")
    ax.set_xlabel("Net P&L ($)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"P&L Distribution: {campaign.strategy_name}")
    ax.legend()
    plt.close(fig)
    return fig


def plot_equity_curves(
    campaign: CampaignResult,
    *,
    sample: int = 50,
    seed: int = 0,
) -> Figure:
    """Spaghetti plot of sampled equity-curve paths."""
    sessions = campaign.sessions
    n = len(sessions)
    count = min(sample, n)

    if count < n:
        rng = Generator(PCG64(seed))
        indices = rng.choice(n, size=count, replace=False)
    else:
        indices = np.arange(n)

    fig, ax = plt.subplots(tight_layout=True)
    for idx in indices:
        s = sessions[int(idx)]
        curve = (s.initial_bankroll, *s.equity_curve)
        ax.plot(range(len(curve)), curve, alpha=0.15, linewidth=0.8, color=_PALETTE[0])

    ax.set_xlabel("Roll")
    ax.set_ylabel("Bankroll ($)")
    ax.set_title(f"Equity Curves (n={count}): {campaign.strategy_name}")
    plt.close(fig)
    return fig


def plot_drawdown_distribution(
    campaign: CampaignResult,
    *,
    bins: int = 50,
) -> Figure:
    """Histogram of maximum drawdown per session."""
    drawdowns = [s.max_drawdown for s in campaign.sessions]
    fig, ax = plt.subplots(tight_layout=True)
    ax.hist(drawdowns, bins=bins, edgecolor="black", linewidth=0.5, alpha=0.7, color=_PALETTE[3])
    ax.set_xlabel("Max Drawdown ($)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Drawdown Distribution: {campaign.strategy_name}")
    plt.close(fig)
    return fig


def plot_comparison(
    campaigns: Sequence[CampaignResult],
    *,
    bins: int = 50,
) -> Figure:
    """Overlaid P&L histograms for head-to-head comparison."""
    fig, ax = plt.subplots(tight_layout=True)
    for i, camp in enumerate(campaigns):
        nets = [s.net for s in camp.sessions]
        color = _PALETTE[i % len(_PALETTE)]
        ax.hist(nets, bins=bins, alpha=0.45, label=camp.strategy_name, color=color)

    ax.axvline(0, color="black", linestyle="--", linewidth=1, label="Break-even")
    ax.set_xlabel("Net P&L ($)")
    ax.set_ylabel("Frequency")
    ax.set_title("P&L Comparison")
    ax.legend()
    plt.close(fig)
    return fig
