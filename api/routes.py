"""API route definitions."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException

from craps_lab.campaign import compare_strategies, run_campaign
from craps_lab.session import SessionConfig
from craps_lab.strategy import PRESETS, Strategy

from .schemas import (
    CompareRequest,
    CompareResponse,
    PresetInfo,
    PresetParam,
    SimulateRequest,
    SimulateResponse,
)
from .serializers import serialize_campaign

router = APIRouter(prefix="/api")

# Strategy metadata for the frontend
_PRESET_META: dict[str, dict[str, object]] = {
    "pass-line-with-odds": {
        "name": "Pass Line with Odds",
        "description": (
            "Pass line on come-out, 3-4-5x odds behind the point. The textbook low-edge play."
        ),
        "params": [
            PresetParam(name="line_amount", default=5, description="Pass line wager"),
        ],
    },
    "iron-cross": {
        "name": "Iron Cross",
        "description": (
            "Field + place 5/6/8. Wins on every number except 7. Feels great until it doesn't."
        ),
        "params": [
            PresetParam(name="line_amount", default=5, description="Pass line wager"),
            PresetParam(name="place_inside", default=6, description="Place 6/8 wager"),
            PresetParam(name="place_outside", default=5, description="Place 5 wager"),
            PresetParam(name="field_amount", default=5, description="Field wager"),
        ],
    },
    "three-point-molly": {
        "name": "Three Point Molly",
        "description": (
            "Pass line + two come bets, all with odds. Three points working at all times."
        ),
        "params": [
            PresetParam(name="line_amount", default=5, description="Line/come wager"),
        ],
    },
}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/presets")
def list_presets() -> list[PresetInfo]:
    results: list[PresetInfo] = []
    for slug in PRESETS:
        meta = _PRESET_META[slug]
        results.append(
            PresetInfo(
                slug=slug,
                name=str(meta["name"]),
                description=str(meta["description"]),
                params=meta["params"],  # type: ignore[arg-type]
            )
        )
    return results


def _make_config(req: SimulateRequest | CompareRequest) -> SessionConfig:
    max_rolls = int(req.hours * req.rolls_per_hour)
    return SessionConfig(
        bankroll=req.bankroll,
        max_rolls=max_rolls,
        stop_win=req.stop_win,
        stop_loss=req.stop_loss,
    )


def _resolve_strategy(slug: str) -> Strategy:
    if slug not in PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {slug}")
    return PRESETS[slug]()


def _display_name(slug: str) -> str:
    return str(_PRESET_META[slug]["name"])


def _resolve_seed(seed: int | None) -> int:
    """Honor caller-supplied seed; otherwise draw a fresh 32-bit seed.

    A fixed default would mean every API call returns bit-identical
    results, which contradicts the showcase's whole pitch.
    """
    return secrets.randbits(32) if seed is None else seed


@router.post("/simulate")
def simulate(req: SimulateRequest) -> SimulateResponse:
    strategy = _resolve_strategy(req.strategy)
    config = _make_config(req)
    seed = _resolve_seed(req.seed)
    result = run_campaign(strategy, config, sessions=req.sessions, base_seed=seed)
    return serialize_campaign(result, display_name=_display_name(req.strategy), seed=seed)


@router.post("/compare")
def compare(req: CompareRequest) -> CompareResponse:
    strategies = [_resolve_strategy(slug) for slug in req.strategies]
    config = _make_config(req)
    seed = _resolve_seed(req.seed)
    results = compare_strategies(strategies, config, sessions=req.sessions, base_seed=seed)
    return CompareResponse(
        results=[
            serialize_campaign(r, display_name=_display_name(slug), seed=seed)
            for slug, r in zip(req.strategies, results, strict=True)
        ],
        seed=seed,
    )
