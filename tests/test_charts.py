"""Tests for chart functions."""

from __future__ import annotations

from matplotlib.figure import Figure

from craps_lab.campaign import CampaignResult, compare_strategies, run_campaign
from craps_lab.charts import (
    plot_comparison,
    plot_drawdown_distribution,
    plot_equity_curves,
    plot_pnl_histogram,
)
from craps_lab.session import SessionConfig
from craps_lab.strategy import IronCross, PassLineWithOdds

_CFG = SessionConfig(bankroll=100, max_rolls=10)
_SESSIONS = 5
_SEED = 42


def _tiny_campaign() -> CampaignResult:
    return run_campaign(PassLineWithOdds(), _CFG, sessions=_SESSIONS, base_seed=_SEED)


# ------------------------------------------------------------------
# plot_pnl_histogram
# ------------------------------------------------------------------


class TestPlotPnlHistogram:
    def test_returns_figure(self) -> None:
        fig = plot_pnl_histogram(_tiny_campaign())
        assert isinstance(fig, Figure)

    def test_axes_has_break_even_line(self) -> None:
        fig = plot_pnl_histogram(_tiny_campaign())
        ax = fig.axes[0]
        # At least one vertical line at x=0.
        lines = [line for line in ax.get_lines() if line.get_xdata()[0] == 0]  # type: ignore[index]
        assert len(lines) >= 1

    def test_title_includes_strategy_name(self) -> None:
        fig = plot_pnl_histogram(_tiny_campaign())
        assert "PassLineWithOdds" in fig.axes[0].get_title()


# ------------------------------------------------------------------
# plot_equity_curves
# ------------------------------------------------------------------


class TestPlotEquityCurves:
    def test_returns_figure(self) -> None:
        fig = plot_equity_curves(_tiny_campaign())
        assert isinstance(fig, Figure)

    def test_plots_all_when_fewer_than_sample(self) -> None:
        camp = _tiny_campaign()
        fig = plot_equity_curves(camp, sample=100)
        ax = fig.axes[0]
        assert len(ax.get_lines()) == len(camp.sessions)

    def test_samples_correct_count(self) -> None:
        camp = run_campaign(PassLineWithOdds(), _CFG, sessions=20, base_seed=_SEED)
        fig = plot_equity_curves(camp, sample=5)
        ax = fig.axes[0]
        assert len(ax.get_lines()) == 5

    def test_deterministic_sampling(self) -> None:
        camp = run_campaign(PassLineWithOdds(), _CFG, sessions=20, base_seed=_SEED)
        fig1 = plot_equity_curves(camp, sample=5, seed=0)
        fig2 = plot_equity_curves(camp, sample=5, seed=0)
        data1 = [line.get_ydata().tolist() for line in fig1.axes[0].get_lines()]  # type: ignore[union-attr]
        data2 = [line.get_ydata().tolist() for line in fig2.axes[0].get_lines()]  # type: ignore[union-attr]
        assert data1 == data2


# ------------------------------------------------------------------
# plot_drawdown_distribution
# ------------------------------------------------------------------


class TestPlotDrawdownDistribution:
    def test_returns_figure(self) -> None:
        fig = plot_drawdown_distribution(_tiny_campaign())
        assert isinstance(fig, Figure)


# ------------------------------------------------------------------
# plot_comparison
# ------------------------------------------------------------------


class TestPlotComparison:
    def test_returns_figure(self) -> None:
        camps = compare_strategies(
            [PassLineWithOdds(), IronCross()], _CFG, sessions=_SESSIONS, base_seed=_SEED
        )
        fig = plot_comparison(camps)
        assert isinstance(fig, Figure)

    def test_legend_has_strategy_names(self) -> None:
        camps = compare_strategies(
            [PassLineWithOdds(), IronCross()], _CFG, sessions=_SESSIONS, base_seed=_SEED
        )
        fig = plot_comparison(camps)
        legend = fig.axes[0].get_legend()
        assert legend is not None
        labels = [t.get_text() for t in legend.get_texts()]
        assert "PassLineWithOdds" in labels
        assert "IronCross" in labels
