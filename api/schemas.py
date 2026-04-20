"""Pydantic request/response models for the craps-lab API."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, model_validator

# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------


def _require_at_least_one_roll(hours: float, rolls_per_hour: int) -> None:
    if int(hours * rolls_per_hour) < 1:
        msg = "hours * rolls_per_hour must yield at least one roll"
        raise ValueError(msg)


class SimulateRequest(BaseModel):
    strategy: str = Field(description="Strategy preset slug")
    bankroll: int = Field(gt=0, description="Starting bankroll in dollars")
    hours: float = Field(gt=0, le=24, default=4.0, description="Hours of play")
    rolls_per_hour: int = Field(gt=0, le=300, default=60)
    stop_win: int | None = Field(default=None, gt=0)
    stop_loss: int | None = Field(default=None, gt=0)
    sessions: int = Field(gt=0, default=10_000, le=100_000)
    seed: int | None = Field(default=None, ge=0, description="Base RNG seed; null draws random")

    @model_validator(mode="after")
    def _check_roll_count(self) -> Self:
        _require_at_least_one_roll(self.hours, self.rolls_per_hour)
        return self


class CompareRequest(BaseModel):
    strategies: list[str] = Field(min_length=2, max_length=5)
    bankroll: int = Field(gt=0)
    hours: float = Field(gt=0, le=24, default=4.0)
    rolls_per_hour: int = Field(gt=0, le=300, default=60)
    stop_win: int | None = Field(default=None, gt=0)
    stop_loss: int | None = Field(default=None, gt=0)
    sessions: int = Field(gt=0, default=10_000, le=100_000)
    seed: int | None = Field(default=None, ge=0, description="Base RNG seed; null draws random")

    @model_validator(mode="after")
    def _check_roll_count(self) -> Self:
        _require_at_least_one_roll(self.hours, self.rolls_per_hour)
        return self


# ------------------------------------------------------------------
# Response models
# ------------------------------------------------------------------


class PresetInfo(BaseModel):
    slug: str
    name: str
    description: str


class SummaryStats(BaseModel):
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
    percentile_10: float
    percentile_25: float
    percentile_75: float
    percentile_90: float
    percentile_95: float
    mean_rolls: float
    mean_drawdown: float
    avg_win: float
    avg_loss: float


class EquityPercentiles(BaseModel):
    rolls: list[int]
    p5: list[float]
    p25: list[float]
    p50: list[float]
    p75: list[float]
    p95: list[float]


class ChartData(BaseModel):
    pnl_values: list[int]
    drawdown_values: list[int]
    equity_percentiles: EquityPercentiles
    equity_sample: list[list[int]]


class SimulateResponse(BaseModel):
    summary: SummaryStats
    charts: ChartData
    seed: int = Field(description="Base seed actually used; rerun with this for identical results")


class CompareResponse(BaseModel):
    results: list[SimulateResponse]
    seed: int = Field(description="Base seed actually used; rerun with this for identical results")
