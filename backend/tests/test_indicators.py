"""Pruebas de cálculos de los 7 módulos, escalas de unidades y manejo robusto de NaN."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.config import SECTOR_ETFS
from app.indicators import (
    compute_all_indicators,
    compute_equal_weight_index,
    rolling_minmax_0_100,
)
from tests.conftest import generate_synthetic_raw_data
from app.data_fetcher import align_all_to_trading_calendar


def test_net_liquidity_unit_unification():
    """WALCL y WTREGEN (millones USD) y RRPONTSYD (miles de millones USD) se unifican a $B."""
    idx = pd.bdate_range("2024-01-02", periods=5)
    df = pd.DataFrame(
        {
            "WALCL": [7_000_000.0] * 5,    # $7,000B
            "WTREGEN": [800_000.0] * 5,    # $800B
            "RRPONTSYD": [400.0] * 5,      # $400B
            "QQQ": [400.0] * 5,
            "SMH": [200.0] * 5,
            "SPY": [500.0] * 5,
        },
        index=idx,
    )
    ind = compute_all_indicators(df)
    assert np.allclose(ind["net_liquidity_bn"], 5_800.0)


def test_credit_spread_bp_conversion_and_priority_buy():
    """BAMLH0A0HYM2 y BAMLC0A4CBBB se convierten de % a pb (x100) y disparan alerta prioritaria."""
    idx = pd.bdate_range("2024-01-02", periods=4)
    df = pd.DataFrame(
        {
            "BAMLH0A0HYM2": [3.50, 5.25, 4.10, 4.10],  # 350, 525 (>500), 410, 410 bp
            "BAMLC0A4CBBB": [1.05, 1.20, 1.35, 1.10],  # 105, 120, 135 (>130), 110 bp
            "QQQ": [400.0] * 4,
            "SMH": [200.0] * 4,
            "SPY": [500.0] * 4,
        },
        index=idx,
    )
    ind = compute_all_indicators(df)
    assert np.allclose(ind["hy_oas_bp"], [350.0, 525.0, 410.0, 410.0])
    assert np.allclose(ind["bbb_oas_bp"], [105.0, 120.0, 135.0, 110.0])
    assert list(ind["credit_priority_buy"]) == [False, True, True, False]


def test_real_rates_cycle_labels_and_bp_deltas():
    """DFII10 calcula deltas en pb a 1M/3M y asigna etiquetas Expansión / Presión de Tipos / Alerta Recesión."""
    idx = pd.bdate_range("2024-01-02", periods=80)
    dfii10 = np.full(80, 1.50)
    dfii10[70:] = 1.95  # +45 bp vs 21d y 63d -> Presión de Tipos
    sahm = np.full(80, 0.10)
    sahm[75:] = 0.55    # >= 0.50 -> Alerta Recesión tiene precedencia

    df = pd.DataFrame(
        {
            "DFII10": dfii10,
            "T10Y2Y": np.full(80, 0.25),
            "SAHMREALTIME": sahm,
            "QQQ": np.full(80, 450.0),
            "SMH": np.full(80, 220.0),
            "SPY": np.full(80, 520.0),
        },
        index=idx,
    )
    ind = compute_all_indicators(df)
    assert pytest.approx(ind["dfii10_chg_1m_bp"].iloc[72], abs=1e-6) == 45.0
    assert pytest.approx(ind["dfii10_chg_3m_bp"].iloc[72], abs=1e-6) == 45.0
    assert ind["cycle_label"].iloc[65] == "Expansión"
    assert ind["cycle_label"].iloc[72] == "Presión de Tipos"
    assert ind["cycle_label"].iloc[77] == "Alerta Recesión"


def test_nan_handling_late_xlc_and_flat_minmax():
    """Sectores con inicio tardío (XLC) y series constantes no generan NaNs indebidos ni divisiones por cero."""
    market, fred = generate_synthetic_raw_data(n_days=900, seed=7, late_xlc=True)
    df = align_all_to_trading_calendar(market, fred)
    ind = compute_all_indicators(df)

    # En día 250 (después del calentamiento SMA200, antes de que exista XLC en día 450):
    # deben contarse 10 sectores válidos, nunca NaN
    assert ind["sectors_valid_count"].iloc[250] == len(SECTOR_ETFS) - 1
    assert pd.notna(ind["pct_sectors_above_sma200"].iloc[250])

    # En día 700 (XLC ya tiene SMA200 válida): los 11 sectores participan
    assert ind["sectors_valid_count"].iloc[700] == len(SECTOR_ETFS)
    assert 0.0 <= ind["pct_sectors_above_sma200"].iloc[700] <= 100.0

    # Ventana plana en rolling_minmax_0_100 debe devolver 50.0 (nunca NaN/inf)
    flat = pd.Series([10.0] * 200, index=pd.bdate_range("2024-01-02", periods=200))
    scaled = rolling_minmax_0_100(flat, window=150, min_periods=50)
    assert np.allclose(scaled.iloc[60:], 50.0)


def test_equal_weight_index_tolerates_leading_nans():
    """compute_equal_weight_index tolera NaNs iniciales y nunca produce infinitos."""
    idx = pd.bdate_range("2024-01-02", periods=10)
    df = pd.DataFrame(
        {
            "XLY": [100.0, 102.0, 104.04, 104.04, 106.12, 108.0, 109.0, 110.0, 111.0, 112.0],
            "XLK": [np.nan, np.nan, np.nan, 200.0, 204.0, 208.0, 210.0, 212.0, 214.0, 216.0],
        },
        index=idx,
    )
    eq = compute_equal_weight_index(df, ("XLY", "XLK"))
    assert eq.iloc[0] == pytest.approx(100.0)
    assert eq.notna().all()
    assert np.isfinite(eq).all()
