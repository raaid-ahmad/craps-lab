"""Streamlit dashboard for craps-lab.

Launch with::

    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

from craps_lab.campaign import CampaignResult, compare_strategies, run_campaign, summarize


def _fmt_pnl(value: float) -> str:
    if value >= 0:
        return f"+${value:,.0f}"
    return f"-${-value:,.0f}"
from craps_lab.charts import (
    plot_comparison,
    plot_drawdown_distribution,
    plot_equity_curves,
    plot_pnl_histogram,
)
from craps_lab.session import SessionConfig
from craps_lab.strategy import PRESETS

st.set_page_config(page_title="craps-lab", layout="wide")

# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------

st.sidebar.title("craps-lab")

strategy_slug = st.sidebar.selectbox(
    "Strategy",
    options=list(PRESETS.keys()),
    format_func=lambda s: s.replace("-", " ").title(),
)

bankroll = st.sidebar.number_input("Bankroll ($)", min_value=1, value=500, step=50)
hours = st.sidebar.number_input("Hours of Play", min_value=0.5, value=4.0, step=0.5)
rolls_per_hour = st.sidebar.number_input("Rolls/Hour", min_value=1, value=60, step=10)
stop_win_input = st.sidebar.number_input(
    "Stop Win ($)", min_value=0, value=0, step=50, help="Net profit to stop at. 0 = disabled."
)
stop_loss_input = st.sidebar.number_input(
    "Stop Loss ($)", min_value=0, value=0, step=50, help="Net loss to stop at. 0 = disabled."
)
num_sessions = st.sidebar.number_input("Sessions", min_value=100, value=10_000, step=1000)

compare_mode = st.sidebar.checkbox("Compare Mode")
strategy_slug_2 = None
if compare_mode:
    other_slugs = [s for s in PRESETS if s != strategy_slug]
    if other_slugs:
        strategy_slug_2 = st.sidebar.selectbox(
            "Compare With",
            options=other_slugs,
            format_func=lambda s: s.replace("-", " ").title(),
        )

run_button = st.sidebar.button("Run Simulation", type="primary")


# ------------------------------------------------------------------
# Cached runners
# ------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _run_single(
    slug: str,
    _bankroll: int,
    _max_rolls: int,
    _stop_win: int | None,
    _stop_loss: int | None,
    _sessions: int,
) -> CampaignResult:
    config = SessionConfig(
        bankroll=_bankroll,
        max_rolls=_max_rolls,
        stop_win=_stop_win,
        stop_loss=_stop_loss,
    )
    return run_campaign(PRESETS[slug](), config, sessions=_sessions, base_seed=0)


@st.cache_data(show_spinner=False)
def _run_comparison(
    slug_1: str,
    slug_2: str,
    _bankroll: int,
    _max_rolls: int,
    _stop_win: int | None,
    _stop_loss: int | None,
    _sessions: int,
) -> tuple[CampaignResult, ...]:
    config = SessionConfig(
        bankroll=_bankroll,
        max_rolls=_max_rolls,
        stop_win=_stop_win,
        stop_loss=_stop_loss,
    )
    return compare_strategies(
        [PRESETS[slug_1](), PRESETS[slug_2]()],
        config,
        sessions=_sessions,
        base_seed=0,
    )


# ------------------------------------------------------------------
# Main area
# ------------------------------------------------------------------

st.title("Craps Strategy Simulator")

if run_button:
    max_rolls = int(hours * rolls_per_hour)
    stop_win = int(stop_win_input) if stop_win_input > 0 else None
    stop_loss = int(stop_loss_input) if stop_loss_input > 0 else None

    if compare_mode and strategy_slug_2:
        with st.spinner("Running comparison..."):
            campaigns = _run_comparison(
                strategy_slug,
                strategy_slug_2,
                int(bankroll),
                max_rolls,
                stop_win,
                stop_loss,
                int(num_sessions),
            )

        cols = st.columns(len(campaigns))
        for col, camp in zip(cols, campaigns):
            with col:
                s = summarize(camp)
                st.subheader(camp.strategy_name)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Win Rate", f"{s.win_rate:.1%}")
                m2.metric("Bust Rate", f"{s.bust_rate:.1%}")
                m3.metric("Mean P&L", _fmt_pnl(s.mean_pnl))
                m4.metric("Median P&L", _fmt_pnl(s.median_pnl))

                st.pyplot(plot_pnl_histogram(camp))
                st.pyplot(plot_equity_curves(camp))

        st.subheader("Head-to-Head P&L Comparison")
        st.pyplot(plot_comparison(list(campaigns)))

    else:
        with st.spinner("Running simulation..."):
            campaign = _run_single(
                strategy_slug,
                int(bankroll),
                max_rolls,
                stop_win,
                stop_loss,
                int(num_sessions),
            )

        s = summarize(campaign)
        st.subheader(campaign.strategy_name)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Win Rate", f"{s.win_rate:.1%}")
        c2.metric("Bust Rate", f"{s.bust_rate:.1%}")
        c3.metric("Mean P&L", _fmt_pnl(s.mean_pnl))
        c4.metric("Median P&L", _fmt_pnl(s.median_pnl))

        st.dataframe(
            {
                "Metric": [
                    "5th Percentile",
                    "25th Percentile",
                    "75th Percentile",
                    "95th Percentile",
                    "Std P&L",
                    "Mean Rolls",
                    "Mean Peak",
                    "Mean Trough",
                    "Mean Drawdown",
                ],
                "Value": [
                    _fmt_pnl(s.percentile_5),
                    _fmt_pnl(s.percentile_25),
                    _fmt_pnl(s.percentile_75),
                    _fmt_pnl(s.percentile_95),
                    f"${s.std_pnl:,.0f}",
                    f"{s.mean_rolls:,.1f}",
                    f"${s.mean_peak:,.0f}",
                    f"${s.mean_trough:,.0f}",
                    f"${s.mean_drawdown:,.0f}",
                ],
            },
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("P&L Distribution")
        st.pyplot(plot_pnl_histogram(campaign))

        st.subheader("Equity Curves")
        st.pyplot(plot_equity_curves(campaign))

        st.subheader("Drawdown Distribution")
        st.pyplot(plot_drawdown_distribution(campaign))

else:
    st.info("Configure a strategy in the sidebar and click **Run Simulation**.")
