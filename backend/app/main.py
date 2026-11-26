"""Servidor REST FastAPI para MacroCompass (Edición Growth & Tech)."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.alerts import evaluate_alert_trigger, format_alert_message
from app.config import load_weights_config
from app.data_fetcher import DataRepository
from app.indicators import compute_all_indicators
from app.scoring import (
    build_backtest_payload,
    build_dashboard_payload,
    compute_module_scores_and_composite,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MacroCompass API (Edición Growth & Tech)",
    version="1.0.0",
    description="Motor de datos macroeconómicos, scoring 0-100, Alerta Temprana Tech y backtest de 10 años.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _EngineCache:
    """Caché en memoria de los DataFrames calculados para respuestas instantáneas (<15ms)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.scored = None
        self.metadata: dict[str, Any] = {}
        self.computed_at: float = 0.0
        self.ttl_seconds: float = 600.0

    def get_scored(self, force_refresh: bool = False) -> tuple[Any, dict[str, Any]]:
        with self._lock:
            now = time.monotonic()
            if (
                not force_refresh
                and self.scored is not None
                and (now - self.computed_at) < self.ttl_seconds
            ):
                return self.scored, self.metadata

            cfg = load_weights_config()
            repo = DataRepository()
            df, metadata = repo.load_aligned_dataframe(
                refresh_if_stale=True,
                force_refresh=force_refresh,
            )
            ind = compute_all_indicators(df, thresholds=cfg.get("thresholds"))
            scored = compute_module_scores_and_composite(ind, config=cfg)

            self.scored = scored
            self.metadata = metadata
            self.computed_at = time.monotonic()
            return self.scored, self.metadata


_cache = _EngineCache()


@app.get("/api/health")
def health() -> dict[str, Any]:
    cfg = load_weights_config()
    return {
        "status": "ok",
        "app": "MacroCompass (Edición Growth & Tech)",
        "weights": cfg["weights"],
        "cached_in_memory": _cache.scored is not None,
        "metadata": _cache.metadata,
    }


@app.get("/api/dashboard")
def get_dashboard() -> dict[str, Any]:
    try:
        scored, metadata = _cache.get_scored(force_refresh=False)
        return build_dashboard_payload(scored, metadata=metadata)
    except Exception as exc:
        logger.exception("Error generando dashboard")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/backtest")
def get_backtest(
    ticker: str = Query(default="QQQ", pattern="^(QQQ|SMH|SPY|qqq|smh|spy)$"),
    years: int = Query(default=10, ge=2, le=20),
) -> dict[str, Any]:
    try:
        scored, _ = _cache.get_scored(force_refresh=False)
        return build_backtest_payload(scored, ticker=ticker, years=years)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error generando backtest")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/refresh")
def refresh_data() -> dict[str, Any]:
    try:
        scored, metadata = _cache.get_scored(force_refresh=True)
        payload = build_dashboard_payload(scored, metadata=metadata)
        return {
            "status": "refreshed",
            "as_of_date": payload["as_of_date"],
            "growth_macro_score": payload["summary"]["growth_macro_score"],
            "metadata": metadata,
        }
    except Exception as exc:
        logger.exception("Error refrescando datos")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/alerts/preview")
def preview_alert() -> dict[str, Any]:
    try:
        scored, metadata = _cache.get_scored(force_refresh=False)
        payload = build_dashboard_payload(scored, metadata=metadata)
        repo = DataRepository()
        last_alert = repo.db.get_last_alert()
        should_send, reasons = evaluate_alert_trigger(payload, last_alert=last_alert, force=False)
        return {
            "should_send": should_send,
            "reasons": reasons,
            "last_alert": last_alert,
            "preview_message": format_alert_message(payload, reasons=reasons, last_alert=last_alert),
        }
    except Exception as exc:
        logger.exception("Error generando vista previa de alerta")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
