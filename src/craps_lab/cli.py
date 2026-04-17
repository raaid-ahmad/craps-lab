"""CLI entry point for craps-lab.

Provides ``run``, ``compare``, and ``list-presets`` commands.
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table as RichTable

from craps_lab.campaign import CampaignSummary, compare_strategies, run_campaign, summarize
from craps_lab.session import SessionConfig
from craps_lab.strategy import PRESETS

app = typer.Typer(name="craps-lab", no_args_is_help=True)
console = Console()

_DEFAULT_ROLLS_PER_HOUR = 60


def _resolve_strategy(slug: str) -> type:
    """Look up a strategy class by slug, or exit with an error."""
    if slug not in PRESETS:
        valid = ", ".join(sorted(PRESETS))
        console.print(f"[red]Unknown strategy:[/red] {slug}")
        console.print(f"Available: {valid}")
        raise typer.Exit(code=1)
    return PRESETS[slug]


def _fmt_pnl(value: float) -> str:
    if value >= 0:
        return f"+${value:,.0f}"
    return f"-${-value:,.0f}"


def _fmt_pct(value: float) -> str:
    return f"{value:.1%}"


def _summary_rows(summary: CampaignSummary) -> list[tuple[str, str]]:
    """Metric/value pairs for display."""
    return [
        ("Win Rate", _fmt_pct(summary.win_rate)),
        ("Bust Rate", _fmt_pct(summary.bust_rate)),
        ("Stop Win Rate", _fmt_pct(summary.stop_win_rate)),
        ("Stop Loss Rate", _fmt_pct(summary.stop_loss_rate)),
        ("Time Limit Rate", _fmt_pct(summary.time_limit_rate)),
        ("Mean P&L", _fmt_pnl(summary.mean_pnl)),
        ("Median P&L", _fmt_pnl(summary.median_pnl)),
        ("Std P&L", f"${summary.std_pnl:,.0f}"),
        ("5th Percentile", _fmt_pnl(summary.percentile_5)),
        ("25th Percentile", _fmt_pnl(summary.percentile_25)),
        ("75th Percentile", _fmt_pnl(summary.percentile_75)),
        ("95th Percentile", _fmt_pnl(summary.percentile_95)),
        ("Mean Rolls", f"{summary.mean_rolls:,.1f}"),
        ("Mean Drawdown", f"${summary.mean_drawdown:,.0f}"),
    ]


@app.command("list-presets")
def list_presets() -> None:
    """List available strategy presets."""
    table = RichTable(title="Strategy Presets", show_header=True)
    table.add_column("Slug", style="bold")
    table.add_column("Description")
    for slug, cls in PRESETS.items():
        desc = (cls.__doc__ or "").split("\n")[0].strip()
        table.add_row(slug, desc)
    console.print(table)


@app.command()
def run(
    strategy: Annotated[str, typer.Option("--strategy", "-s", help="Strategy preset slug")],
    bankroll: Annotated[int, typer.Option("--bankroll", "-b", help="Starting bankroll ($)")],
    hours: Annotated[float, typer.Option("--hours", "-H", help="Hours of play")],
    sessions: Annotated[int, typer.Option("--sessions", "-n", help="Number of sessions")] = 10_000,
    stop_win: Annotated[int | None, typer.Option(help="Stop-win net profit threshold ($)")] = None,
    stop_loss: Annotated[int | None, typer.Option(help="Stop-loss net loss threshold ($)")] = None,
    rolls_per_hour: Annotated[int, typer.Option(help="Rolls per hour")] = _DEFAULT_ROLLS_PER_HOUR,
    seed: Annotated[int, typer.Option(help="Base RNG seed")] = 0,
) -> None:
    """Run a strategy for many sessions and show aggregate stats."""
    strategy_cls = _resolve_strategy(strategy)
    max_rolls = int(hours * rolls_per_hour)
    config = SessionConfig(
        bankroll=bankroll,
        max_rolls=max_rolls,
        stop_win=stop_win,
        stop_loss=stop_loss,
    )

    console.print(
        f"[bold]{strategy_cls.__name__}[/bold] | "
        f"${bankroll:,} bankroll | {hours}h ({max_rolls} rolls) | "
        f"{sessions:,} sessions"
    )

    with console.status(f"Running {sessions:,} sessions..."):
        campaign = run_campaign(strategy_cls(), config, sessions=sessions, base_seed=seed)

    summary = summarize(campaign)
    table = RichTable(title=campaign.strategy_name, show_header=True)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    for metric, value in _summary_rows(summary):
        table.add_row(metric, value)
    console.print(table)


@app.command()
def compare(
    strategies: Annotated[
        str,
        typer.Option(help="Comma-separated slugs, e.g. pass-line-with-odds,iron-cross"),
    ],
    bankroll: Annotated[int, typer.Option("--bankroll", "-b", help="Starting bankroll ($)")],
    hours: Annotated[float, typer.Option("--hours", "-H", help="Hours of play")],
    sessions: Annotated[int, typer.Option("--sessions", "-n", help="Number of sessions")] = 10_000,
    stop_win: Annotated[int | None, typer.Option(help="Stop-win net profit threshold ($)")] = None,
    stop_loss: Annotated[int | None, typer.Option(help="Stop-loss net loss threshold ($)")] = None,
    rolls_per_hour: Annotated[int, typer.Option(help="Rolls per hour")] = _DEFAULT_ROLLS_PER_HOUR,
    seed: Annotated[int, typer.Option(help="Base RNG seed")] = 0,
) -> None:
    """Compare strategies head-to-head on shared dice sequences."""
    slugs = [s.strip() for s in strategies.split(",")]
    strategy_objs = [_resolve_strategy(s)() for s in slugs]

    max_rolls = int(hours * rolls_per_hour)
    config = SessionConfig(
        bankroll=bankroll,
        max_rolls=max_rolls,
        stop_win=stop_win,
        stop_loss=stop_loss,
    )

    console.print(f"${bankroll:,} bankroll | {hours}h ({max_rolls} rolls) | {sessions:,} sessions")

    with console.status(f"Running {sessions:,} sessions per strategy..."):
        campaigns = compare_strategies(strategy_objs, config, sessions=sessions, base_seed=seed)

    table = RichTable(title="Strategy Comparison", show_header=True)
    table.add_column("Metric", style="bold")
    for camp in campaigns:
        table.add_column(camp.strategy_name, justify="right")

    summaries = [summarize(c) for c in campaigns]
    for metric, values in _comparison_rows(summaries):
        table.add_row(metric, *values)

    console.print(table)


def _comparison_rows(
    summaries: list[CampaignSummary],
) -> list[tuple[str, list[str]]]:
    return [
        ("Win Rate", [_fmt_pct(s.win_rate) for s in summaries]),
        ("Bust Rate", [_fmt_pct(s.bust_rate) for s in summaries]),
        ("Stop Win Rate", [_fmt_pct(s.stop_win_rate) for s in summaries]),
        ("Stop Loss Rate", [_fmt_pct(s.stop_loss_rate) for s in summaries]),
        ("Time Limit Rate", [_fmt_pct(s.time_limit_rate) for s in summaries]),
        ("Mean P&L", [_fmt_pnl(s.mean_pnl) for s in summaries]),
        ("Median P&L", [_fmt_pnl(s.median_pnl) for s in summaries]),
        ("Std P&L", [f"${s.std_pnl:,.0f}" for s in summaries]),
        ("5th Percentile", [_fmt_pnl(s.percentile_5) for s in summaries]),
        ("95th Percentile", [_fmt_pnl(s.percentile_95) for s in summaries]),
        ("Mean Rolls", [f"{s.mean_rolls:,.1f}" for s in summaries]),
        ("Mean Drawdown", [f"${s.mean_drawdown:,.0f}" for s in summaries]),
    ]
