"""Tests de contrato HTTP para los endpoints de FastAPI."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import main as app_main
from app.config import load_weights_config
from app.indicators import compute_all_indicators
from app.scoring import compute_module_scores_and_composite


def test_fastapi_endpoints_with_synthetic_data(synthetic_aligned_df, monkeypatch):
    cfg = load_weights_config()
    ind = compute_all_indicators(synthetic_aligned_df, cfg["thresholds"])
    scored = compute_module_scores_and_composite(ind, cfg)
    fake_meta = {
        "fred_source_mode": "fred_csv_fallback",
        "last_fetched_utc": "2026-11-26T00:00:00+00:00",
        "as_of_date": scored.index[-1].strftime("%Y-%m-%d"),
        "credit_history": {
            "hy_min_date": "2023-11-27",
            "bbb_min_date": "2023-11-27",
            "is_limited_csv_window": True,
        },
        "refresh_errors": [],
    }

    monkeypatch.setattr(app_main._cache, "get_scored", lambda force_refresh=False: (scored, fake_meta))

    client = TestClient(app_main.app)

    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_dash = client.get("/api/dashboard")
    assert r_dash.status_code == 200
    dash = r_dash.json()
    assert len(dash["modules"]) == 7
    assert 0.0 <= dash["summary"]["growth_macro_score"] <= 100.0
    assert len(dash["summary"]["early_warning_tech"]["conditions"]) == 4

    for ticker in ("QQQ", "SMH", "SPY"):
        r_bt = client.get(f"/api/backtest?ticker={ticker}&years=5")
        assert r_bt.status_code == 200
        bt = r_bt.json()
        assert bt["ticker"] == ticker
        assert len(bt["series"]) > 50
