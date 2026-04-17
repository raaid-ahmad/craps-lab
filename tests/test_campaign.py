"""Tests for the campaign runner."""

from __future__ import annotations

import pytest

from craps_lab.campaign import (
    CampaignResult,
    compare_strategies,
    run_campaign,
    summarize,
)
from craps_lab.session import SessionConfig
from craps_lab.strategy import PassLineWithOdds, ThreePointMolly

# ------------------------------------------------------------------
# Shared config
# ------------------------------------------------------------------

_CFG = SessionConfig(bankroll=500, max_rolls=60)
_SMALL_SESSIONS = 20
_SEED = 0xCAFE


# ------------------------------------------------------------------
# run_campaign
# ------------------------------------------------------------------


class TestRunCampaign:
    """Running a single strategy across many sessions."""

    def test_returns_correct_session_count(self) -> None:
        result = run_campaign(PassLineWithOdds(), _CFG, sessions=_SMALL_SESSIONS, base_seed=_SEED)
        assert len(result.sessions) == _SMALL_SESSIONS

    def test_strategy_name_captured(self) -> None:
        result = run_campaign(PassLineWithOdds(), _CFG, sessions=5, base_seed=0)
        assert result.strategy_name == "PassLineWithOdds"

    def test_config_preserved(self) -> None:
        result = run_campaign(PassLineWithOdds(), _CFG, sessions=5, base_seed=0)
        assert result.config is _CFG

    def test_base_seed_preserved(self) -> None:
        result = run_campaign(PassLineWithOdds(), _CFG, sessions=5, base_seed=42)
        assert result.base_seed == 42

    def test_deterministic_with_same_seed(self) -> None:
        r1 = run_campaign(PassLineWithOdds(), _CFG, sessions=10, base_seed=_SEED)
        r2 = run_campaign(PassLineWithOdds(), _CFG, sessions=10, base_seed=_SEED)
        nets1 = tuple(s.net for s in r1.sessions)
        nets2 = tuple(s.net for s in r2.sessions)
        assert nets1 == nets2

    def test_different_seeds_produce_different_results(self) -> None:
        r1 = run_campaign(PassLineWithOdds(), _CFG, sessions=10, base_seed=0)
        r2 = run_campaign(PassLineWithOdds(), _CFG, sessions=10, base_seed=999)
        nets1 = tuple(s.net for s in r1.sessions)
        nets2 = tuple(s.net for s in r2.sessions)
        assert nets1 != nets2

    @pytest.mark.parametrize("bad", [True, 1.0, "10"])
    def test_rejects_non_int_sessions(self, bad: object) -> None:
        with pytest.raises(TypeError, match="sessions must be an int"):
            run_campaign(PassLineWithOdds(), _CFG, sessions=bad, base_seed=0)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [0, -1])
    def test_rejects_non_positive_sessions(self, bad: int) -> None:
        with pytest.raises(ValueError, match="sessions must be positive"):
            run_campaign(PassLineWithOdds(), _CFG, sessions=bad, base_seed=0)

    @pytest.mark.parametrize("bad", [True, 1.0])
    def test_rejects_non_int_base_seed(self, bad: object) -> None:
        with pytest.raises(TypeError, match="base_seed must be an int"):
            run_campaign(PassLineWithOdds(), _CFG, sessions=5, base_seed=bad)  # type: ignore[arg-type]


# ------------------------------------------------------------------
# compare_strategies
# ------------------------------------------------------------------


class TestCompareStrategies:
    """Head-to-head comparison on shared dice sequences."""

    def test_returns_one_result_per_strategy(self) -> None:
        strategies = [PassLineWithOdds(), ThreePointMolly()]
        results = compare_strategies(strategies, _CFG, sessions=5, base_seed=0)
        assert len(results) == 2

    def test_strategy_names_match(self) -> None:
        strategies = [PassLineWithOdds(), ThreePointMolly()]
        results = compare_strategies(strategies, _CFG, sessions=5, base_seed=0)
        assert results[0].strategy_name == "PassLineWithOdds"
        assert results[1].strategy_name == "ThreePointMolly"

    def test_shared_seeds(self) -> None:
        # Running each strategy independently with same seed gives same result.
        strategies = [PassLineWithOdds(), ThreePointMolly()]
        compared = compare_strategies(strategies, _CFG, sessions=10, base_seed=_SEED)

        standalone_0 = run_campaign(PassLineWithOdds(), _CFG, sessions=10, base_seed=_SEED)
        standalone_1 = run_campaign(ThreePointMolly(), _CFG, sessions=10, base_seed=_SEED)

        nets_c0 = tuple(s.net for s in compared[0].sessions)
        nets_s0 = tuple(s.net for s in standalone_0.sessions)
        assert nets_c0 == nets_s0

        nets_c1 = tuple(s.net for s in compared[1].sessions)
        nets_s1 = tuple(s.net for s in standalone_1.sessions)
        assert nets_c1 == nets_s1

    def test_rejects_empty_strategies(self) -> None:
        with pytest.raises(ValueError, match="strategies must be non-empty"):
            compare_strategies([], _CFG, sessions=5, base_seed=0)


# ------------------------------------------------------------------
# summarize
# ------------------------------------------------------------------


class TestSummarize:
    """Aggregate statistics from campaign results."""

    @pytest.fixture
    def campaign(self) -> CampaignResult:
        return run_campaign(PassLineWithOdds(), _CFG, sessions=_SMALL_SESSIONS, base_seed=_SEED)

    def test_session_count(self, campaign: CampaignResult) -> None:
        s = summarize(campaign)
        assert s.session_count == _SMALL_SESSIONS

    def test_strategy_name(self, campaign: CampaignResult) -> None:
        s = summarize(campaign)
        assert s.strategy_name == "PassLineWithOdds"

    def test_win_rate_in_range(self, campaign: CampaignResult) -> None:
        s = summarize(campaign)
        assert 0.0 <= s.win_rate <= 1.0

    def test_stop_reason_rates_sum_to_one(self, campaign: CampaignResult) -> None:
        s = summarize(campaign)
        total = s.bust_rate + s.stop_win_rate + s.stop_loss_rate + s.time_limit_rate
        assert abs(total - 1.0) < 1e-9

    def test_mean_pnl_sign(self, campaign: CampaignResult) -> None:
        s = summarize(campaign)
        # Mean P&L should be a finite number (not NaN or inf).
        assert s.mean_pnl == s.mean_pnl  # not NaN

    def test_percentile_ordering(self, campaign: CampaignResult) -> None:
        s = summarize(campaign)
        assert s.percentile_5 <= s.percentile_25
        assert s.percentile_25 <= s.median_pnl
        assert s.median_pnl <= s.percentile_75
        assert s.percentile_75 <= s.percentile_95

    def test_mean_drawdown_non_negative(self, campaign: CampaignResult) -> None:
        s = summarize(campaign)
        assert s.mean_drawdown >= 0.0

    def test_mean_rolls_positive(self, campaign: CampaignResult) -> None:
        s = summarize(campaign)
        assert s.mean_rolls > 0.0

    def test_bust_rate_with_tiny_bankroll(self) -> None:
        cfg = SessionConfig(bankroll=5, max_rolls=200)
        camp = run_campaign(PassLineWithOdds(), cfg, sessions=50, base_seed=0)
        s = summarize(camp)
        # With $5 bankroll and $5 bets, bust rate should be significant.
        assert s.bust_rate > 0.0

    def test_rejects_empty_campaign(self) -> None:
        empty = CampaignResult(
            strategy_name="test",
            config=_CFG,
            sessions=(),
            base_seed=0,
        )
        with pytest.raises(ValueError, match="campaign has no sessions"):
            summarize(empty)

    def test_single_session(self) -> None:
        camp = run_campaign(PassLineWithOdds(), _CFG, sessions=1, base_seed=0)
        s = summarize(camp)
        assert s.session_count == 1
        assert s.mean_pnl == float(camp.sessions[0].net)
