"""Fixtures sintéticas reproducibles para pruebas unitarias y anti-look-ahead."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.config import ALL_MARKET_TICKERS, FRED_SERIES, load_weights_config
from app.data_fetcher import align_all_to_trading_calendar


def generate_synthetic_raw_data(
    n_days: int = 1400,
    seed: int = 42,
    late_xlc: bool = True,
    late_credit_csv: bool = False,
) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """Genera series sintéticas realistas de mercado (diarias) y FRED (diarias/semanales/mensuales)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2019-01-02", periods=n_days)

    market: dict[str, pd.Series] = {}
    base_ret = rng.normal(0.0004, 0.011, size=n_days)

    for idx, ticker in enumerate(ALL_MARKET_TICKERS):
        if ticker == "^VXN":
            vals = np.clip(22.0 + np.cumsum(rng.normal(0.0, 0.45, size=n_days)), 12.0, 48.0)
        elif ticker == "^VIX":
            vals = np.clip(18.0 + np.cumsum(rng.normal(0.0, 0.35, size=n_days)), 10.0, 45.0)
        elif ticker == "^VIX3M":
            vals = np.clip(20.0 + np.cumsum(rng.normal(0.0, 0.22, size=n_days)), 13.0, 40.0)
        else:
            idio = rng.normal(0.0001 * ((idx % 5) - 2), 0.006, size=n_days)
            vals = 100.0 * np.exp(np.cumsum(base_ret + idio))
        s = pd.Series(vals, index=dates, name=ticker, dtype=float)
        if late_xlc and ticker == "XLC":
            s = s.iloc[450:]  # Simular nacimiento tardío de XLC
        market[ticker] = s

    # Series FRED con sus frecuencias reales
    wed_dates = pd.date_range(dates[0], dates[-1], freq="W-WED")
    fri_dates = pd.date_range(dates[0], dates[-1], freq="W-FRI")
    month_dates = pd.date_range(dates[0], dates[-1], freq="MS")

    fred: dict[str, pd.Series] = {
        # WALCL y WTREGEN en Millones USD (como en FRED real)
        "WALCL": pd.Series(
            7_000_000.0 + np.cumsum(rng.normal(2_000.0, 25_000.0, size=len(wed_dates))),
            index=wed_dates,
            name="WALCL",
        ),
        "WTREGEN": pd.Series(
            np.clip(600_000.0 + np.cumsum(rng.normal(0.0, 20_000.0, size=len(wed_dates))), 100_000.0, 1_500_000.0),
            index=wed_dates,
            name="WTREGEN",
        ),
        # RRPONTSYD en Miles de Millones USD (diaria)
        "RRPONTSYD": pd.Series(
            np.clip(500.0 + np.cumsum(rng.normal(0.0, 12.0, size=n_days)), 0.0, 2_500.0),
            index=dates,
            name="RRPONTSYD",
        ),
        # NFCI semanal (viernes)
        "NFCI": pd.Series(
            np.clip(-0.35 + np.cumsum(rng.normal(0.0, 0.04, size=len(fri_dates))), -0.9, 1.5),
            index=fri_dates,
            name="NFCI",
        ),
        # DFII10 diaria (%)
        "DFII10": pd.Series(
            np.clip(1.4 + np.cumsum(rng.normal(0.0, 0.03, size=n_days)), -1.0, 3.0),
            index=dates,
            name="DFII10",
        ),
        # T10Y2Y diaria (%)
        "T10Y2Y": pd.Series(
            np.clip(0.3 + np.cumsum(rng.normal(0.0, 0.02, size=n_days)), -1.1, 1.8),
            index=dates,
            name="T10Y2Y",
        ),
        # SAHMREALTIME mensual (día 1 de cada mes)
        "SAHMREALTIME": pd.Series(
            np.clip(0.10 + rng.normal(0.0, 0.08, size=len(month_dates)), -0.1, 0.45),
            index=month_dates,
            name="SAHMREALTIME",
        ),
        # Credit spreads en porcentaje (ej. 3.60 -> 360 bp)
        "BAMLH0A0HYM2": pd.Series(
            np.clip(3.7 + np.cumsum(rng.normal(0.0, 0.05, size=n_days)), 2.5, 8.0),
            index=dates,
            name="BAMLH0A0HYM2",
        ),
        "BAMLC0A4CBBB": pd.Series(
            np.clip(1.15 + np.cumsum(rng.normal(0.0, 0.015, size=n_days)), 0.75, 2.5),
            index=dates,
            name="BAMLC0A4CBBB",
        ),
    }

    if late_credit_csv:
        fred["BAMLH0A0HYM2"] = fred["BAMLH0A0HYM2"].iloc[750:]
        fred["BAMLC0A4CBBB"] = fred["BAMLC0A4CBBB"].iloc[750:]

    assert set(fred.keys()) == set(FRED_SERIES)
    return market, fred


@pytest.fixture
def synthetic_aligned_df() -> pd.DataFrame:
    cfg = load_weights_config()
    market, fred = generate_synthetic_raw_data(n_days=1400, seed=42)
    return align_all_to_trading_calendar(
        market_series=market,
        fred_series=fred,
        publication_lags=cfg["publication_lags"],
    )
