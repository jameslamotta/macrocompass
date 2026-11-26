"""Cálculo estrictamente causal de los indicadores de los 7 módulos de MacroCompass.

Todas las funciones operan exclusivamente sobre observaciones <= t (sin look-ahead bias)
y preservan correctamente los valores NaN sin propagarlos innecesariamente entre módulos.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.config import CYCLICAL_ETFS, DEFENSIVE_ETFS, SECTOR_ETFS


def _safe_col(df: pd.DataFrame, col: str) -> pd.Series:
    """Devuelve la columna como Serie float alineada al índice o NaN si no existe."""
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").astype(float)
    return pd.Series(np.nan, index=df.index, dtype=float, name=col)


def rolling_minmax_0_100(
    series: pd.Series,
    window: int = 504,
    min_periods: int = 126,
) -> pd.Series:
    """Normalización min-max estrictamente causal en [0, 100] sobre ventana móvil."""
    s = pd.to_numeric(series, errors="coerce").astype(float)
    roll_min = s.rolling(window=window, min_periods=min_periods).min()
    roll_max = s.rolling(window=window, min_periods=min_periods).max()
    denom = roll_max - roll_min

    out = pd.Series(np.nan, index=s.index, dtype=float)
    valid = s.notna() & roll_min.notna() & roll_max.notna()
    nonzero = valid & (denom > 1e-12)
    flat = valid & (denom <= 1e-12)

    out.loc[nonzero] = ((s.loc[nonzero] - roll_min.loc[nonzero]) / denom.loc[nonzero]) * 100.0
    out.loc[flat] = 50.0
    return out.clip(0.0, 100.0)


def rolling_percentile_0_100(
    series: pd.Series,
    window: int = 2520,
    min_periods: int = 126,
) -> pd.Series:
    """Percentil móvil estrictamente causal (0-100): % de observaciones en la ventana <= valor actual."""
    s = pd.to_numeric(series, errors="coerce").astype(float)

    def _pct_rank(arr: np.ndarray) -> float:
        cur = arr[-1]
        if np.isnan(cur):
            return np.nan
        valid = arr[~np.isnan(arr)]
        if valid.size < min_periods:
            return np.nan
        return float(np.mean(valid <= cur) * 100.0)

    return s.rolling(window=window, min_periods=min_periods).apply(_pct_rank, raw=True)


def compute_equal_weight_index(df: pd.DataFrame, tickers: tuple[str, ...]) -> pd.Series:
    """Construye un índice equiponderado de rentabilidad diaria acumulada (base 100, causal).

    Evita sesgos por precio nominal de cada ETF y tolera ETFs de inicio tardío sin romper la serie.
    """
    available = [t for t in tickers if t in df.columns]
    if not available:
        return pd.Series(np.nan, index=df.index, dtype=float)

    prices = df[available].apply(pd.to_numeric, errors="coerce")
    daily_rets = prices.pct_change(periods=1, fill_method=None)
    mean_ret = daily_rets.mean(axis=1, skipna=True)

    # Identificar primera fecha con al menos un precio válido
    has_any_price = prices.notna().any(axis=1)
    if not has_any_price.any():
        return pd.Series(np.nan, index=df.index, dtype=float)

    first_valid_pos = int(np.argmax(has_any_price.to_numpy()))
    clean_ret = mean_ret.fillna(0.0).copy()
    clean_ret.iloc[: first_valid_pos + 1] = 0.0

    idx_series = (1.0 + clean_ret).cumprod() * 100.0
    idx_series.iloc[:first_valid_pos] = np.nan
    return idx_series


def compute_all_indicators(
    df: pd.DataFrame,
    thresholds: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Calcula todos los indicadores de los 7 módulos en un DataFrame diario estrictamente causal."""
    th = thresholds or {}
    res = pd.DataFrame(index=df.index.copy())

    # Precios de referencia para backtest y triggers
    for ticker in ("QQQ", "SMH", "SPY"):
        res[f"price_{ticker.lower()}"] = _safe_col(df, ticker)

    # ------------------------------------------------------------------
    # Módulo 1: Liquidez Neta de la Fed y Condiciones Financieras (20%)
    # WALCL y WTREGEN están en Millones USD -> /1000 para Miles de Millones USD.
    # RRPONTSYD ya está en Miles de Millones USD.
    # ------------------------------------------------------------------
    walcl_bn = _safe_col(df, "WALCL") / 1000.0
    tga_bn = _safe_col(df, "WTREGEN") / 1000.0
    rrp_bn = _safe_col(df, "RRPONTSYD")

    net_liq_bn = walcl_bn - tga_bn - rrp_bn
    res["walcl_bn"] = walcl_bn
    res["tga_bn"] = tga_bn
    res["rrp_bn"] = rrp_bn
    res["net_liquidity_bn"] = net_liq_bn
    res["net_liq_chg_3m_bn"] = net_liq_bn - net_liq_bn.shift(63)
    res["net_liq_roc_3m_pct"] = (net_liq_bn / net_liq_bn.shift(63) - 1.0) * 100.0
    res["nfci"] = _safe_col(df, "NFCI")

    # ------------------------------------------------------------------
    # Módulo 2: Tipos Reales y Ciclo Económico (15%)
    # ------------------------------------------------------------------
    dfii10 = _safe_col(df, "DFII10")
    t10y2y = _safe_col(df, "T10Y2Y")
    sahm = _safe_col(df, "SAHMREALTIME")

    dfii10_chg_1m_bp = (dfii10 - dfii10.shift(21)) * 100.0
    dfii10_chg_3m_bp = (dfii10 - dfii10.shift(63)) * 100.0
    dfii10_max_shock_bp = pd.concat([dfii10_chg_1m_bp, dfii10_chg_3m_bp], axis=1).max(axis=1)

    res["dfii10"] = dfii10
    res["dfii10_chg_1m_bp"] = dfii10_chg_1m_bp
    res["dfii10_chg_3m_bp"] = dfii10_chg_3m_bp
    res["dfii10_max_shock_bp"] = dfii10_max_shock_bp
    res["t10y2y"] = t10y2y
    res["sahm"] = sahm

    shock_th = float(th.get("real_rates_shock_bp", 35.0))
    sahm_th = float(th.get("sahm_recession", 0.50))
    cycle_label = pd.Series("Expansión", index=df.index, dtype=object)
    cycle_label = cycle_label.where(~(dfii10_max_shock_bp >= shock_th), "Presión de Tipos")
    cycle_label = cycle_label.where(~(sahm >= sahm_th), "Alerta Recesión")
    res["cycle_label"] = cycle_label

    # ------------------------------------------------------------------
    # Módulo 3: Sobreextensión Tech, Semis y Factor Growth (15%)
    # ------------------------------------------------------------------
    qqq = res["price_qqq"]
    smh = res["price_smh"]
    iwf = _safe_col(df, "IWF")
    iwd = _safe_col(df, "IWD")

    qqq_sma200 = qqq.rolling(window=200, min_periods=200).mean()
    smh_sma200 = smh.rolling(window=200, min_periods=200).mean()

    res["qqq_sma200"] = qqq_sma200
    res["smh_sma200"] = smh_sma200
    res["qqq_dist_sma200_pct"] = (qqq / qqq_sma200 - 1.0) * 100.0
    res["smh_dist_sma200_pct"] = (smh / smh_sma200 - 1.0) * 100.0

    iwf_iwd_ratio = iwf / iwd.replace(0.0, np.nan)
    res["iwf_iwd_ratio"] = iwf_iwd_ratio
    res["iwf_iwd_2y_minmax"] = rolling_minmax_0_100(iwf_iwd_ratio, window=504, min_periods=126)

    # ------------------------------------------------------------------
    # Módulo 4: Amplitud de Mercado — "How Many Stocks Take Part" (15%)
    # ------------------------------------------------------------------
    rsp = _safe_col(df, "RSP")
    spy = res["price_spy"]
    qqqe = _safe_col(df, "QQQE")

    rsp_spy_ratio = rsp / spy.replace(0.0, np.nan)
    qqqe_qqq_ratio = qqqe / qqq.replace(0.0, np.nan)
    rsp_spy_sma200 = rsp_spy_ratio.rolling(window=200, min_periods=200).mean()
    qqqe_qqq_sma200 = qqqe_qqq_ratio.rolling(window=200, min_periods=200).mean()

    res["rsp_spy_ratio"] = rsp_spy_ratio
    res["rsp_spy_sma200"] = rsp_spy_sma200
    res["rsp_spy_roc_3m_pct"] = (rsp_spy_ratio / rsp_spy_ratio.shift(63) - 1.0) * 100.0
    res["qqqe_qqq_ratio"] = qqqe_qqq_ratio
    res["qqqe_qqq_sma200"] = qqqe_qqq_sma200
    res["qqqe_qqq_roc_1m_pct"] = (qqqe_qqq_ratio / qqqe_qqq_ratio.shift(21) - 1.0) * 100.0
    res["qqqe_qqq_roc_3m_pct"] = (qqqe_qqq_ratio / qqqe_qqq_ratio.shift(63) - 1.0) * 100.0

    # % de los 11 ETFs sectoriales por encima de su SMA 200 (denominador dinámico según historia disponible)
    above_counts = pd.Series(0.0, index=df.index, dtype=float)
    valid_counts = pd.Series(0.0, index=df.index, dtype=float)
    for sec in SECTOR_ETFS:
        sec_p = _safe_col(df, sec)
        sec_sma = sec_p.rolling(window=200, min_periods=200).mean()
        is_valid = sec_p.notna() & sec_sma.notna()
        valid_counts = valid_counts + is_valid.astype(float)
        above_counts = above_counts + (is_valid & (sec_p > sec_sma)).astype(float)

    res["sectors_valid_count"] = valid_counts
    res["sectors_above_sma200_count"] = above_counts
    res["pct_sectors_above_sma200"] = np.where(
        valid_counts > 0,
        (above_counts / valid_counts) * 100.0,
        np.nan,
    )

    # Divergencia bajista: QQQ cerca de máximos de 3M mientras QQQE/QQQ cae activamente
    near_high_factor = float(th.get("qqq_near_high_pct", 0.97))
    drop_1m_th = float(th.get("qqqe_qqq_1m_drop_pct", -1.5))
    qqq_3m_high = qqq.rolling(window=63, min_periods=21).max()
    qqq_near_3m_high = qqq.notna() & qqq_3m_high.notna() & (qqq >= near_high_factor * qqq_3m_high)
    qqqe_below_sma = qqqe_qqq_ratio.notna() & qqqe_qqq_sma200.notna() & (qqqe_qqq_ratio < qqqe_qqq_sma200)
    qqqe_dropping_1m = res["qqqe_qqq_roc_1m_pct"].notna() & (res["qqqe_qqq_roc_1m_pct"] <= drop_1m_th)
    res["qqq_near_3m_high"] = qqq_near_3m_high
    res["breadth_bearish_divergence"] = qqq_near_3m_high & qqqe_below_sma & qqqe_dropping_1m

    # ------------------------------------------------------------------
    # Módulo 5: Volatilidad Nasdaq y Estructura Temporal (15%)
    # ------------------------------------------------------------------
    vxn = _safe_col(df, "^VXN")
    vix = _safe_col(df, "^VIX")
    vix3m = _safe_col(df, "^VIX3M")
    vix_term_ratio = vix / vix3m.replace(0.0, np.nan)

    res["vxn"] = vxn
    res["vix"] = vix
    res["vix3m"] = vix3m
    res["vix_term_ratio"] = vix_term_ratio

    # ------------------------------------------------------------------
    # Módulo 6: Precio del Riesgo — "The Price of Risk" (10%)
    # FRED devuelve porcentaje -> multiplicar por 100 para puntos básicos (bp)
    # ------------------------------------------------------------------
    hy_bp = _safe_col(df, "BAMLH0A0HYM2") * 100.0
    bbb_bp = _safe_col(df, "BAMLC0A4CBBB") * 100.0

    res["hy_oas_bp"] = hy_bp
    res["hy_chg_1m_bp"] = hy_bp - hy_bp.shift(21)
    res["hy_chg_3m_bp"] = hy_bp - hy_bp.shift(63)
    res["hy_pct_10y"] = rolling_percentile_0_100(hy_bp, window=2520, min_periods=126)
    res["hy_median_hist_bp"] = hy_bp.rolling(window=2520, min_periods=63).median()

    res["bbb_oas_bp"] = bbb_bp
    res["bbb_chg_1m_bp"] = bbb_bp - bbb_bp.shift(21)
    res["bbb_chg_3m_bp"] = bbb_bp - bbb_bp.shift(63)
    res["bbb_pct_10y"] = rolling_percentile_0_100(bbb_bp, window=2520, min_periods=126)
    res["bbb_median_hist_bp"] = bbb_bp.rolling(window=2520, min_periods=63).median()

    hy_buy_th = float(th.get("hy_priority_buy_bp", 500.0))
    bbb_buy_th = float(th.get("bbb_priority_buy_bp", 130.0))
    res["credit_priority_buy"] = (
        (hy_bp.notna() & (hy_bp > hy_buy_th))
        | (bbb_bp.notna() & (bbb_bp > bbb_buy_th))
    )

    # ------------------------------------------------------------------
    # Módulo 7: Cíclicos vs. Defensivos — "Cyclicals Against Defensives" (10%)
    # ------------------------------------------------------------------
    cyc_idx = compute_equal_weight_index(df, CYCLICAL_ETFS)
    def_idx = compute_equal_weight_index(df, DEFENSIVE_ETFS)
    cyc_def_ratio = cyc_idx / def_idx.replace(0.0, np.nan)
    cyc_def_raw_0_100 = rolling_minmax_0_100(cyc_def_ratio, window=504, min_periods=126)
    cyc_def_ma5 = cyc_def_raw_0_100.rolling(window=5, min_periods=1).mean()

    xlk = _safe_col(df, "XLK")
    xlp = _safe_col(df, "XLP")
    xlk_xlp_ratio = xlk / xlp.replace(0.0, np.nan)
    xlk_xlp_2y_pct = rolling_percentile_0_100(xlk_xlp_ratio, window=504, min_periods=126)

    res["cyc_def_ratio"] = cyc_def_ratio
    res["cyc_def_raw_0_100"] = cyc_def_raw_0_100
    res["cyc_def_ma5"] = cyc_def_ma5
    res["xlk_xlp_ratio"] = xlk_xlp_ratio
    res["xlk_xlp_2y_pct"] = xlk_xlp_2y_pct

    return res
