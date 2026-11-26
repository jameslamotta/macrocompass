"""Pruebas del motor de scoring 0-100, regímenes, renormalización y Alerta Temprana Tech."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from app.config import load_weights_config
from app.data_fetcher import align_all_to_trading_calendar
from app.indicators import compute_all_indicators
from app.scoring import classify_regime, compute_module_scores_and_composite
from tests.conftest import generate_synthetic_raw_data


def _make_single_row_indicators(**overrides) -> pd.DataFrame:
    """Crea un DataFrame de 1 fila con indicadores neutros personalizables para probar scoring."""
    base = {
        "price_qqq": 500.0,
        "price_smh": 250.0,
        "price_spy": 580.0,
        "walcl_bn": 6800.0,
        "tga_bn": 750.0,
        "rrp_bn": 50.0,
        "net_liquidity_bn": 6000.0,
        "net_liq_chg_3m_bn": 50.0,
        "net_liq_roc_3m_pct": 1.0,
        "nfci": -0.30,
        "dfii10": 1.80,
        "dfii10_chg_1m_bp": 5.0,
        "dfii10_chg_3m_bp": 8.0,
        "dfii10_max_shock_bp": 8.0,
        "t10y2y": 0.30,
        "sahm": 0.10,
        "cycle_label": "Expansión",
        "qqq_sma200": 480.0,
        "smh_sma200": 240.0,
        "qqq_dist_sma200_pct": 4.0,
        "smh_dist_sma200_pct": 4.0,
        "iwf_iwd_ratio": 1.8,
        "iwf_iwd_2y_minmax": 50.0,
        "rsp_spy_ratio": 0.30,
        "rsp_spy_sma200": 0.30,
        "rsp_spy_roc_3m_pct": 0.5,
        "qqqe_qqq_ratio": 0.18,
        "qqqe_qqq_sma200": 0.18,
        "qqqe_qqq_roc_1m_pct": 0.0,
        "qqqe_qqq_roc_3m_pct": 0.0,
        "sectors_valid_count": 11.0,
        "sectors_above_sma200_count": 6.0,
        "pct_sectors_above_sma200": 54.5,
        "qqq_near_3m_high": False,
        "breadth_bearish_divergence": False,
        "vxn": 22.0,
        "vix": 18.0,
        "vix3m": 20.0,
        "vix_term_ratio": 0.90,
        "hy_oas_bp": 380.0,
        "hy_chg_1m_bp": 0.0,
        "hy_chg_3m_bp": 0.0,
        "hy_pct_10y": 50.0,
        "hy_median_hist_bp": 380.0,
        "bbb_oas_bp": 115.0,
        "bbb_chg_1m_bp": 0.0,
        "bbb_chg_3m_bp": 0.0,
        "bbb_pct_10y": 50.0,
        "bbb_median_hist_bp": 115.0,
        "credit_priority_buy": False,
        "cyc_def_ratio": 1.1,
        "cyc_def_raw_0_100": 50.0,
        "cyc_def_ma5": 50.0,
        "xlk_xlp_ratio": 2.5,
        "xlk_xlp_2y_pct": 50.0,
    }
    base.update(overrides)
    return pd.DataFrame([base], index=pd.DatetimeIndex(["2026-11-25"]))


def test_scores_always_bounded_0_100(synthetic_aligned_df):
    cfg = load_weights_config()
    ind = compute_all_indicators(synthetic_aligned_df, cfg["thresholds"])
    scored = compute_module_scores_and_composite(ind, cfg)

    score_cols = [
        "score_liquidity",
        "score_real_rates",
        "score_tech_extension",
        "score_market_breadth",
        "score_volatility",
        "score_price_of_risk",
        "score_cyclicals_defensives",
        "growth_macro_score",
    ]
    for col in score_cols:
        valid = scored[col].dropna()
        assert not valid.empty, f"Sin valores válidos en {col}"
        assert (valid >= 0.0).all() and (valid <= 100.0).all(), f"Fuera de rango [0, 100] en {col}"


def test_weight_renormalization_when_credit_missing():
    """En modo CSV público sin datos previos de crédito, el score compuesto sigue siendo válido (sin NaN)."""
    cfg = load_weights_config()
    market, fred = generate_synthetic_raw_data(n_days=1100, seed=99, late_credit_csv=True)
    df = align_all_to_trading_calendar(market, fred, cfg["publication_lags"])
    ind = compute_all_indicators(df, cfg["thresholds"])
    scored = compute_module_scores_and_composite(ind, cfg)

    # En día 500 aún no hay HY/BBB (empiezan en día 750), pero growth_macro_score debe estar presente y en [0, 100]
    assert pd.isna(scored["score_price_of_risk"].iloc[500])
    assert pd.notna(scored["growth_macro_score"].iloc[500])
    assert 0.0 <= scored["growth_macro_score"].iloc[500] <= 100.0


def test_credit_priority_buy_asymmetry():
    """Cuando HY > 500 bp o BBB > 130 bp, el score del Módulo 6 cae a zona verde de compra (<= 16)."""
    row_hy = _make_single_row_indicators(hy_oas_bp=540.0, bbb_oas_bp=110.0, credit_priority_buy=True)
    scored_hy = compute_module_scores_and_composite(row_hy)
    assert scored_hy["score_price_of_risk"].iloc[0] <= 16.0

    row_bbb = _make_single_row_indicators(hy_oas_bp=390.0, bbb_oas_bp=142.0, credit_priority_buy=True)
    scored_bbb = compute_module_scores_and_composite(row_bbb)
    assert scored_bbb["score_price_of_risk"].iloc[0] <= 16.0


def test_early_warning_tech_exact_3_of_4_combinations():
    """Alerta Temprana Tech se activa exactamente con >= 3 de 4 condiciones y nunca con <= 2."""
    cond_overrides = {
        "c1": {"qqq_dist_sma200_pct": 17.5},          # QQQ > +15%
        "c2": {"vxn": 15.8},                          # ^VXN < 17.5
        "c3": {"dfii10_max_shock_bp": 38.0},          # DFII10 > +30 bp
        "c4": {"breadth_bearish_divergence": True},   # Divergencia QQQE/QQQ
    }

    keys = list(cond_overrides.keys())
    for k in range(0, 5):
        for combo in itertools.combinations(keys, k):
            merged = {}
            for key in combo:
                merged.update(cond_overrides[key])
            row = _make_single_row_indicators(**merged)
            scored = compute_module_scores_and_composite(row)
            assert int(scored["ew_conditions_met"].iloc[0]) == k
            assert bool(scored["tech_early_warning"].iloc[0]) is (k >= 3), (
                f"Falló combinación {combo} (k={k})"
            )

    # También comprobar las ramas alternativas (OR) de c1 (SMH > +22%), c3 (Liq 3M < 0%) y c4 (IWF/IWD > 85)
    alt_row = _make_single_row_indicators(
        qqq_dist_sma200_pct=10.0,
        smh_dist_sma200_pct=24.0,
        vxn=16.5,
        net_liq_roc_3m_pct=-1.2,
        dfii10_max_shock_bp=5.0,
        breadth_bearish_divergence=False,
        iwf_iwd_2y_minmax=89.0,
    )
    alt_scored = compute_module_scores_and_composite(alt_row)
    assert int(alt_scored["ew_conditions_met"].iloc[0]) == 4
    assert bool(alt_scored["tech_early_warning"].iloc[0]) is True


def test_regime_classification_and_playbook():
    assert classify_regime(85.0)["label"] == "Euforia extrema"
    assert "FOMO" in classify_regime(85.0)["playbook"]
    assert classify_regime(72.0)["label"] == "Calentamiento"
    assert classify_regime(50.0)["label"] == "Neutral"
    assert classify_regime(25.0)["label"] == "Miedo / Estrés"
    cap = classify_regime(12.0, sahm_value=0.60)
    assert cap["label"] == "Capitulación"
    assert cap["sahm_caution"] is True
    assert "Sahm >= 0.50" in cap["playbook"]
