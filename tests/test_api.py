"""Tests for the FastAPI backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from api.main import app

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


# Small payload shared across happy-path tests — keeps the Monte Carlo
# runs fast while still exercising the serializer end-to-end.
_FAST_BODY = {
    "strategy": "pass-line-with-odds",
    "bankroll": 200,
    "hours": 0.1,
    "rolls_per_hour": 60,
    "sessions": 20,
}


class TestHealth:
    def test_returns_ok(self, client: TestClient) -> None:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


class TestPresets:
    def test_lists_all_three_presets(self, client: TestClient) -> None:
        res = client.get("/api/presets")
        assert res.status_code == 200
        slugs = {p["slug"] for p in res.json()}
        assert slugs == {"pass-line-with-odds", "iron-cross", "three-point-molly"}

    def test_entries_have_display_metadata(self, client: TestClient) -> None:
        entry = next(p for p in client.get("/api/presets").json() if p["slug"] == "iron-cross")
        assert entry["name"]
        assert entry["description"]
        assert len(entry["params"]) >= 1


class TestSimulate:
    def test_returns_summary_and_charts(self, client: TestClient) -> None:
        res = client.post("/api/simulate", json=_FAST_BODY)
        assert res.status_code == 200
        body = res.json()
        assert body["summary"]["session_count"] == _FAST_BODY["sessions"]
        assert body["summary"]["strategy_name"]
        assert len(body["charts"]["pnl_values"]) == _FAST_BODY["sessions"]
        assert len(body["charts"]["drawdown_values"]) == _FAST_BODY["sessions"]
        assert body["charts"]["equity_percentiles"]["rolls"]
        assert body["charts"]["equity_sample"]

    def test_percentile_bands_are_ordered(self, client: TestClient) -> None:
        body = client.post("/api/simulate", json=_FAST_BODY).json()
        ep = body["charts"]["equity_percentiles"]
        for i in range(len(ep["rolls"])):
            assert ep["p5"][i] <= ep["p25"][i] <= ep["p50"][i] <= ep["p75"][i] <= ep["p95"][i]

    def test_unknown_strategy_returns_400(self, client: TestClient) -> None:
        res = client.post("/api/simulate", json={**_FAST_BODY, "strategy": "not-a-real-preset"})
        assert res.status_code == 400
        assert "not-a-real-preset" in res.json()["detail"]

    def test_non_positive_bankroll_rejected(self, client: TestClient) -> None:
        assert client.post("/api/simulate", json={**_FAST_BODY, "bankroll": 0}).status_code == 422

    def test_session_count_cap_enforced(self, client: TestClient) -> None:
        res = client.post("/api/simulate", json={**_FAST_BODY, "sessions": 200_000})
        assert res.status_code == 422


class TestCompare:
    def test_head_to_head_returns_one_result_per_strategy(self, client: TestClient) -> None:
        body = {
            **{k: v for k, v in _FAST_BODY.items() if k != "strategy"},
            "strategies": ["pass-line-with-odds", "iron-cross"],
        }
        res = client.post("/api/compare", json=body)
        assert res.status_code == 200
        results = res.json()["results"]
        assert len(results) == 2
        assert {r["summary"]["strategy_name"] for r in results} == {
            "Pass Line with Odds",
            "Iron Cross",
        }

    def test_single_strategy_rejected(self, client: TestClient) -> None:
        body = {
            **{k: v for k, v in _FAST_BODY.items() if k != "strategy"},
            "strategies": ["pass-line-with-odds"],
        }
        assert client.post("/api/compare", json=body).status_code == 422

    def test_unknown_strategy_returns_400(self, client: TestClient) -> None:
        body = {
            **{k: v for k, v in _FAST_BODY.items() if k != "strategy"},
            "strategies": ["pass-line-with-odds", "bogus"],
        }
        assert client.post("/api/compare", json=body).status_code == 400
