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
    SimulateRequest,
    SimulateResponse,
)
from .serializers import serialize_campaign

router = APIRouter(prefix="/api")

# Strategy metadata for the frontend
_PRESET_META: dict[str, dict[str, str]] = {
    "pass-line-with-odds": {
        "name": "Pass Line with Odds",
        "description": (
            "Pass line on come-out, 3-4-5x odds behind the point. The textbook low-edge play."
        ),
    },
    "iron-cross": {
        "name": "Iron Cross",
        "description": (
            "Field + place 5/6/8. Wins on every number except 7. Feels great until it doesn't."
        ),
    },
    "three-point-molly": {
        "name": "Three Point Molly",
        "description": (
            "Pass line + two come bets, all with odds. Three points working at all times."
        ),
    },
}


def _check_preset_metadata_matches_registry() -> None:
    """Fail at import if a strategy was added without UI metadata.

    Without this guard, /api/presets crashes with a 500 the first time
    someone hits it after registering a new preset.
    """
    missing = set(PRESETS) - set(_PRESET_META)
    extra = set(_PRESET_META) - set(PRESETS)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing metadata: {sorted(missing)}")
        if extra:
            details.append(f"orphan metadata: {sorted(extra)}")
        msg = "Preset metadata is out of sync with PRESETS — " + "; ".join(details)
        raise RuntimeError(msg)


_check_preset_metadata_matches_registry()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/presets")
def list_presets() -> list[PresetInfo]:
    return [
        PresetInfo(slug=slug, name=meta["name"], description=meta["description"])
        for slug, meta in ((s, _PRESET_META[s]) for s in PRESETS)
    ]


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
    return _PRESET_META[slug]["name"]


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
