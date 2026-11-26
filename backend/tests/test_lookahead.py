"""Pruebas estrictas de ausencia de look-ahead bias (causalidad e invarianza por truncado)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.config import load_weights_config
from app.data_fetcher import align_all_to_trading_calendar, align_series_to_calendar
from app.indicators import compute_all_indicators
from app.scoring import compute_module_scores_and_composite
from tests.conftest import generate_synthetic_raw_data


def test_publication_lags_prevent_future_leakage():
    """WALCL semanal (+1 BDay) y SAHMREALTIME mensual (+35 días naturales) no se filtran antes de su publicación."""
    calendar = pd.bdate_range("2024-01-02", "2024-05-31")

    # WALCL fechado miércoles 2024-02-07 -> disponible jueves 2024-02-08 (+1 día hábil)
    walcl = pd.Series(
        [7_000_000.0, 7_500_000.0],
        index=pd.to_datetime(["2024-01-31", "2024-02-07"]),
        name="WALCL",
    )
    aligned_walcl = align_series_to_calendar(
        walcl, calendar, lag_spec={"unit": "business_days", "lag": 1}
    )
    assert aligned_walcl.loc[pd.Timestamp("2024-02-07")] == 7_000_000.0
    assert aligned_walcl.loc[pd.Timestamp("2024-02-08")] == 7_500_000.0

    # SAHMREALTIME fechado 2024-03-01 (datos de marzo) -> disponible +35 días (2024-04-05)
    sahm = pd.Series(
        [0.10, 0.60],
        index=pd.to_datetime(["2024-02-01", "2024-03-01"]),
        name="SAHMREALTIME",
    )
    aligned_sahm = align_series_to_calendar(
        sahm, calendar, lag_spec={"unit": "calendar_days", "lag": 35}
    )
    # Durante marzo y principios de abril todavía NO se puede conocer el 0.60 de marzo
    assert aligned_sahm.loc[pd.Timestamp("2024-03-15")] == 0.10
    assert aligned_sahm.loc[pd.Timestamp("2024-04-04")] == 0.10
    assert aligned_sahm.loc[pd.Timestamp("2024-04-05")] == 0.60


def test_strict_no_lookahead_prefix_invariance():
    """Truncar todas las series en T_cut e inyectar shocks futuros NO altera ningún cálculo <= T_cut."""
    cfg = load_weights_config()
    market_full, fred_full = generate_synthetic_raw_data(n_days=1300, seed=123, late_xlc=True)

    # Elegir fecha de corte intermedia con suficiente historia previa (> 700 días)
    all_dates = market_full["SPY"].index
    cutoff_date = all_dates[900]

    # Escenario A: datos truncados estrictamente a <= cutoff_date
    market_trunc = {k: v[v.index <= cutoff_date].copy() for k, v in market_full.items()}
    fred_trunc = {k: v[v.index <= cutoff_date].copy() for k, v in fred_full.items()}

    df_trunc = align_all_to_trading_calendar(market_trunc, fred_trunc, cfg["publication_lags"])
    scored_trunc = compute_module_scores_and_composite(
        compute_all_indicators(df_trunc, cfg["thresholds"]),
        config=cfg,
    )

    # Escenario B: historia completa con shocks extremos inyectados DESPUÉS de cutoff_date
    market_shocked = {}
    for k, v in market_full.items():
        s = v.copy()
        s.loc[s.index > cutoff_date] = s.loc[s.index > cutoff_date] * (4.0 if k == "QQQ" else 0.25)
        market_shocked[k] = s

    fred_shocked = {}
    for k, v in fred_full.items():
        s = v.copy()
        s.loc[s.index > cutoff_date] = s.loc[s.index > cutoff_date] + 999.0
        fred_shocked[k] = s

    df_full = align_all_to_trading_calendar(market_shocked, fred_shocked, cfg["publication_lags"])
    scored_full = compute_module_scores_and_composite(
        compute_all_indicators(df_full, cfg["thresholds"]),
        config=cfg,
    )

    scored_full_prefix = scored_full.loc[scored_trunc.index]

    numeric_cols = [
        c for c in scored_trunc.columns if pd.api.types.is_numeric_dtype(scored_trunc[c])
    ]
    for col in numeric_cols:
        a = scored_trunc[col].to_numpy(dtype=float)
        b = scored_full_prefix[col].to_numpy(dtype=float)
        assert np.allclose(a, b, rtol=0.0, atol=1e-9, equal_nan=True), (
            f"Look-ahead bias detectado en columna '{col}'"
        )

    for bool_col in ("breadth_bearish_divergence", "credit_priority_buy", "tech_early_warning"):
        assert (scored_trunc[bool_col].fillna(False) == scored_full_prefix[bool_col].fillna(False)).all(), (
            f"Look-ahead bias detectado en flag '{bool_col}'"
        )
