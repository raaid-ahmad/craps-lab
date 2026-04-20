"""Pydantic request/response models for the craps-lab API."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------


class SimulateRequest(BaseModel):
    strategy: str = Field(description="Strategy preset slug")
    bankroll: int = Field(gt=0, description="Starting bankroll in dollars")
    hours: float = Field(gt=0, default=4.0, description="Hours of play")
    rolls_per_hour: int = Field(gt=0, default=60)
    stop_win: int | None = Field(default=None, gt=0)
    stop_loss: int | None = Field(default=None, gt=0)
    sessions: int = Field(gt=0, default=10_000, le=100_000)
    seed: int | None = Field(default=None, ge=0, description="Base RNG seed; null draws random")


class CompareRequest(BaseModel):
    strategies: list[str] = Field(min_length=2, max_length=5)
    bankroll: int = Field(gt=0)
    hours: float = Field(gt=0, default=4.0)
    rolls_per_hour: int = Field(gt=0, default=60)
    stop_win: int | None = Field(default=None, gt=0)
    stop_loss: int | None = Field(default=None, gt=0)
    sessions: int = Field(gt=0, default=10_000, le=100_000)
    seed: int | None = Field(default=None, ge=0, description="Base RNG seed; null draws random")


# ------------------------------------------------------------------
# Response models
# ------------------------------------------------------------------


class PresetParam(BaseModel):
    name: str
    default: int
    description: str


class PresetInfo(BaseModel):
    slug: str
    name: str
    description: str
    params: list[PresetParam]


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
