"""Motor de scoring (0-100), Alerta Temprana Tech, Playbook y Backtest de 10 años."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from app.config import load_weights_config


def piecewise_score(
    series: pd.Series,
    xp: list[float],
    fp: list[float],
) -> pd.Series:
    """Interpolación lineal por tramos en [0, 100] que preserva NaNs de forma exacta."""
    s = pd.to_numeric(series, errors="coerce").astype(float)
    arr = s.to_numpy(dtype=float)
    out = np.full(arr.shape, np.nan, dtype=float)
    valid = ~np.isnan(arr)
    if valid.any():
        out[valid] = np.interp(arr[valid], xp, fp)
    return pd.Series(np.clip(out, 0.0, 100.0), index=s.index, dtype=float)


def _weighted_blend(components: list[tuple[pd.Series, float]]) -> pd.Series:
    """Combina múltiples sub-scores en [0, 100] renormalizando pesos cuando hay NaNs."""
    index = components[0][0].index
    num = pd.Series(0.0, index=index, dtype=float)
    den = pd.Series(0.0, index=index, dtype=float)
    for series, weight in components:
        valid = series.notna()
        num = num + series.fillna(0.0) * weight * valid.astype(float)
        den = den + weight * valid.astype(float)
    out = np.where(den > 0.0, num / den, np.nan)
    return pd.Series(np.clip(out, 0.0, 100.0), index=index, dtype=float)


def compute_module_scores_and_composite(
    ind: pd.DataFrame,
    config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Calcula scores 0-100 por módulo, Growth Macro Score compuesto y Alerta Temprana Tech."""
    cfg = config or load_weights_config()
    weights = cfg["weights"]
    ew_cfg = cfg["early_warning_tech"]
    th = cfg.get("thresholds", {})

    scored = ind.copy()

    # ------------------------------------------------------------------
    # Módulo 1: Liquidez Neta (60%) + NFCI (40%)
    # Liquidez contrayéndose con mercado en máximos = riesgo elevado (score alto).
    # Inyección fuerte de liquidez o condiciones tensas (NFCI > 0) = zona de compra (score bajo).
    # ------------------------------------------------------------------
    liq_roc_score = piecewise_score(
        ind["net_liq_roc_3m_pct"],
        xp=[-8.0, -4.0, -1.5, 0.0, 2.5, 6.0, 12.0],
        fp=[95.0, 84.0, 70.0, 52.0, 38.0, 20.0, 5.0],
    )
    # Factor de régimen de mercado: contracción de liquidez eleva riesgo de techo
    # cuando QQQ cotiza en máximos/sobre SMA200, no tras desplomes > -10% bajo SMA200.
    market_height_factor = piecewise_score(
        ind["qqq_dist_sma200_pct"],
        xp=[-15.0, -8.0, 0.0, 8.0, 16.0],
        fp=[15.0, 30.0, 55.0, 85.0, 100.0],
    ) / 100.0
    contracting_at_highs = (
        ind["net_liq_roc_3m_pct"].notna()
        & (ind["net_liq_roc_3m_pct"] < 0.0)
        & ind["qqq_near_3m_high"].fillna(False)
    )
    # Si el mercado ya cayó fuertemente (market_height_factor bajo), amortiguar el riesgo de techo
    liq_adj = pd.Series(
        np.where(
            liq_roc_score.notna(),
            np.where(
                market_height_factor.notna() & (liq_roc_score > 50.0),
                50.0 * market_height_factor + (liq_roc_score - 50.0) * market_height_factor,
                liq_roc_score,
            )
            + np.where(contracting_at_highs, 10.0, 0.0),
            np.nan,
        ),
        index=ind.index,
        dtype=float,
    ).clip(0.0, 100.0)

    nfci_score = piecewise_score(
        ind["nfci"],
        xp=[-0.85, -0.60, -0.40, -0.15, 0.10, 0.50, 1.20],
        fp=[86.0, 66.0, 50.0, 35.0, 20.0, 6.0, 0.0],
    )
    scored["score_liquidity"] = _weighted_blend([(liq_adj, 0.60), (nfci_score, 0.40)])

    # ------------------------------------------------------------------
    # Módulo 2: Tipos Reales (DFII10 nivel + shock 1M/3M), T10Y2Y y Sahm
    # Un repunte rápido > +35 bp en 1-3M eleva fuertemente el riesgo para múltiplos Growth.
    # ------------------------------------------------------------------
    rate_shock_score = piecewise_score(
        ind["dfii10_max_shock_bp"],
        xp=[-65.0, -35.0, -15.0, 0.0, 20.0, 35.0, 55.0, 80.0],
        fp=[5.0, 18.0, 34.0, 46.0, 62.0, 82.0, 94.0, 100.0],
    )
    rate_level_score = piecewise_score(
        ind["dfii10"],
        xp=[-1.0, 0.0, 1.0, 2.0, 2.8, 3.5],
        fp=[25.0, 35.0, 45.0, 56.0, 72.0, 86.0],
    )
    m2_base = _weighted_blend([(rate_shock_score, 0.72), (rate_level_score, 0.28)])

    # Si Sahm >= 0.50 y tipos reales ya están cayendo (pánico recesivo / pivote),
    # el riesgo de múltiplos cede hacia zona de acumulación escalonada.
    sahm_recession = ind["sahm"].notna() & (ind["sahm"] >= float(th.get("sahm_recession", 0.50)))
    rates_falling = ind["dfii10_chg_3m_bp"].notna() & (ind["dfii10_chg_3m_bp"] < -20.0)
    m2_adjusted = np.where(
        sahm_recession & rates_falling,
        np.minimum(m2_base, 22.0),
        m2_base,
    )
    # Si hay choque agudo de tipos reales (> +35 bp), garantizar lectura elevada de riesgo (>= 78)
    acute_rate_shock = ind["dfii10_max_shock_bp"].notna() & (
        ind["dfii10_max_shock_bp"] >= float(th.get("real_rates_shock_bp", 35.0))
    )
    m2_adjusted = np.where(acute_rate_shock & ~sahm_recession, np.maximum(m2_adjusted, 78.0), m2_adjusted)
    scored["score_real_rates"] = pd.Series(m2_adjusted, index=ind.index, dtype=float).clip(0.0, 100.0)

    # ------------------------------------------------------------------
    # Módulo 3: Sobreextensión Tech (QQQ), Semis (SMH) y Factor Growth (IWF/IWD)
    # ------------------------------------------------------------------
    qqq_ext_score = piecewise_score(
        ind["qqq_dist_sma200_pct"],
        xp=[-20.0, -10.0, -4.0, 0.0, 8.0, 16.0, 24.0],
        fp=[0.0, 12.0, 28.0, 44.0, 64.0, 86.0, 100.0],
    )
    smh_ext_score = piecewise_score(
        ind["smh_dist_sma200_pct"],
        xp=[-28.0, -15.0, -6.0, 0.0, 12.0, 25.0, 38.0],
        fp=[0.0, 12.0, 28.0, 44.0, 64.0, 86.0, 100.0],
    )
    growth_factor_score = ind["iwf_iwd_2y_minmax"].clip(0.0, 100.0)
    m3_base = _weighted_blend(
        [(qqq_ext_score, 0.40), (smh_ext_score, 0.35), (growth_factor_score, 0.25)]
    )
    # En capitulación clara de QQQ (< -10%) o SMH (< -15%), el sesgo relativo Growth/Value
    # no debe ocultar la sobreventa absoluta en precios
    deep_tech_washout = (
        (ind["qqq_dist_sma200_pct"].notna() & (ind["qqq_dist_sma200_pct"] <= float(th.get("qqq_capitulation_pct", -10.0))))
        & (ind["smh_dist_sma200_pct"].notna() & (ind["smh_dist_sma200_pct"] <= float(th.get("smh_capitulation_pct", -15.0))))
    )
    scored["score_tech_extension"] = pd.Series(
        np.where(m3_base.notna() & deep_tech_washout, np.minimum(m3_base, 14.0), m3_base),
        index=ind.index,
        dtype=float,
    ).clip(0.0, 100.0)

    # ------------------------------------------------------------------
    # Módulo 4: Amplitud de Mercado ("How Many Stocks Take Part")
    # Base = % sectores > SMA 200; divergencia bajista en máximos suma prima de riesgo.
    # ------------------------------------------------------------------
    breadth_base = ind["pct_sectors_above_sma200"].clip(0.0, 100.0)
    div_flag = ind["breadth_bearish_divergence"].fillna(False)
    scored["score_market_breadth"] = pd.Series(
        np.where(breadth_base.notna(), np.clip(breadth_base + np.where(div_flag, 15.0, 0.0), 0.0, 100.0), np.nan),
        index=ind.index,
        dtype=float,
    )

    # ------------------------------------------------------------------
    # Módulo 5: Volatilidad Nasdaq (^VXN) y Estructura Temporal (^VIX / ^VIX3M)
    # Complacencia (^VXN < 17 y ratio < 0.85) -> >85; Capitulación (^VXN > 32 y ratio > 1.0) -> <15
    # ------------------------------------------------------------------
    vxn_score = piecewise_score(
        ind["vxn"],
        xp=[13.0, 17.0, 20.0, 24.0, 32.0, 42.0],
        fp=[100.0, 85.0, 66.0, 45.0, 15.0, 0.0],
    )
    term_score = piecewise_score(
        ind["vix_term_ratio"],
        xp=[0.78, 0.85, 0.90, 0.95, 1.00, 1.15],
        fp=[100.0, 85.0, 66.0, 44.0, 15.0, 0.0],
    )
    scored["score_volatility"] = _weighted_blend([(vxn_score, 0.55), (term_score, 0.45)])

    # ------------------------------------------------------------------
    # Módulo 6: Precio del Riesgo ("The Price of Risk" — HY OAS & BBB OAS)
    # Rol asimétrico: peso moderado en techos, pero alerta prioritaria de compra en estrés
    # ------------------------------------------------------------------
    hy_score = piecewise_score(
        ind["hy_oas_bp"],
        xp=[260.0, 330.0, 400.0, 500.0, 650.0, 850.0],
        fp=[88.0, 72.0, 50.0, 15.0, 5.0, 0.0],
    )
    bbb_score = piecewise_score(
        ind["bbb_oas_bp"],
        xp=[80.0, 100.0, 118.0, 130.0, 170.0, 240.0],
        fp=[88.0, 70.0, 46.0, 15.0, 5.0, 0.0],
    )
    m6_base = _weighted_blend([(hy_score, 0.60), (bbb_score, 0.40)])
    credit_buy = ind["credit_priority_buy"].fillna(False)
    scored["score_price_of_risk"] = pd.Series(
        np.where(m6_base.notna() & credit_buy, np.minimum(m6_base, 16.0), m6_base),
        index=ind.index,
        dtype=float,
    )

    # ------------------------------------------------------------------
    # Módulo 7: Cíclicos vs. Defensivos (75%) + Percentil 2Y XLK/XLP (25%)
    # ------------------------------------------------------------------
    scored["score_cyclicals_defensives"] = _weighted_blend(
        [
            (ind["cyc_def_ma5"].clip(0.0, 100.0), 0.75),
            (ind["xlk_xlp_2y_pct"].clip(0.0, 100.0), 0.25),
        ]
    )

    # ------------------------------------------------------------------
    # Score Compuesto: Growth Macro Score (0-100) con renormalización dinámica de pesos
    # ------------------------------------------------------------------
    module_weight_pairs = [
        (scored["score_liquidity"], float(weights["liquidity"])),
        (scored["score_real_rates"], float(weights["real_rates"])),
        (scored["score_tech_extension"], float(weights["tech_extension"])),
        (scored["score_market_breadth"], float(weights["market_breadth"])),
        (scored["score_volatility"], float(weights["volatility"])),
        (scored["score_price_of_risk"], float(weights["price_of_risk"])),
        (scored["score_cyclicals_defensives"], float(weights["cyclicals_defensives"])),
    ]
    scored["growth_macro_score"] = _weighted_blend(module_weight_pairs)

    # ------------------------------------------------------------------
    # Alerta Temprana Tech (Override táctico): >= 3 de 4 condiciones simultáneas
    # ------------------------------------------------------------------
    cond_1 = (
        (ind["qqq_dist_sma200_pct"].notna() & (ind["qqq_dist_sma200_pct"] > float(ew_cfg["qqq_sma200_pct"])))
        | (ind["smh_dist_sma200_pct"].notna() & (ind["smh_dist_sma200_pct"] > float(ew_cfg["smh_sma200_pct"])))
    )
    cond_2 = ind["vxn"].notna() & (ind["vxn"] < float(ew_cfg["vxn_below"]))
    cond_3 = (
        (ind["net_liq_roc_3m_pct"].notna() & (ind["net_liq_roc_3m_pct"] < float(ew_cfg["net_liq_3m_below_pct"])))
        | (ind["dfii10_max_shock_bp"].notna() & (ind["dfii10_max_shock_bp"] > float(ew_cfg["dfii10_rise_bp"])))
    )
    cond_4 = (
        ind["breadth_bearish_divergence"].fillna(False)
        | (ind["iwf_iwd_2y_minmax"].notna() & (ind["iwf_iwd_2y_minmax"] > float(ew_cfg["iwf_iwd_above"])))
    )

    scored["ew_cond_1_extension"] = cond_1
    scored["ew_cond_2_vxn"] = cond_2
    scored["ew_cond_3_liq_rates"] = cond_3
    scored["ew_cond_4_breadth_growth"] = cond_4
    scored["ew_conditions_met"] = (
        cond_1.astype(int) + cond_2.astype(int) + cond_3.astype(int) + cond_4.astype(int)
    )
    scored["tech_early_warning"] = scored["ew_conditions_met"] >= int(ew_cfg.get("min_conditions", 3))

    return scored


def classify_regime(
    score: float,
    sahm_value: float | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Clasifica el Growth Macro Score en su régimen y devuelve el Playbook exacto."""
    cfg = config or load_weights_config()
    regimes = cfg["regimes"]
    clamped = float(np.clip(score, 0.0, 100.0)) if score is not None and not math.isnan(score) else 50.0

    selected = regimes[2]  # Neutral por defecto
    for reg in regimes:
        if float(reg["min_score"]) <= clamped <= float(reg["max_score"]) + 1e-6:
            selected = reg
            break

    playbook = str(selected["playbook"])
    sahm_warning = bool(
        sahm_value is not None
        and not math.isnan(sahm_value)
        and sahm_value >= float(cfg.get("thresholds", {}).get("sahm_recession", 0.50))
    )
    return {
        "key": selected["key"],
        "label": selected["label"],
        "color": selected["color"],
        "playbook": playbook,
        "sahm_caution": sahm_warning,
    }


def _clean_float(val: Any, digits: int = 2) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, digits)


def _fmt_signed(val: float | None, suffix: str = "", digits: int = 1) -> str:
    if val is None:
        return "N/D"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.{digits}f}{suffix}"


def _series_to_points(
    df: pd.DataFrame,
    cols: dict[str, str],
    years: int | None = None,
    stride: int = 1,
    digits: int = 2,
) -> list[dict[str, Any]]:
    """Convierte columnas seleccionadas a lista JSON compacta para Recharts."""
    sub = df
    if years is not None and not df.empty:
        cutoff = df.index[-1] - pd.DateOffset(years=years)
        sub = df[df.index >= cutoff]

    if stride > 1 and len(sub) > stride:
        idx_positions = list(range(0, len(sub), stride))
        if idx_positions[-1] != len(sub) - 1:
            idx_positions.append(len(sub) - 1)
        sub = sub.iloc[idx_positions]

    points: list[dict[str, Any]] = []
    for dt, row in sub.iterrows():
        item: dict[str, Any] = {"date": pd.Timestamp(dt).strftime("%Y-%m-%d")}
        has_any = False
        for out_key, col_name in cols.items():
            v = _clean_float(row[col_name], digits=digits) if col_name in sub.columns else None
            item[out_key] = v
            if v is not None:
                has_any = True
        if has_any:
            points.append(item)
    return points


def build_dashboard_payload(
    scored: pd.DataFrame,
    metadata: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye el JSON completo para la vista principal de los 7 módulos + Playbook."""
    cfg = config or load_weights_config()
    weights = cfg["weights"]
    ew_cfg = cfg["early_warning_tech"]

    valid_scores = scored.dropna(subset=["growth_macro_score"])
    if valid_scores.empty:
        raise ValueError("No hay suficientes datos históricos para calcular el Growth Macro Score.")

    last_dt = valid_scores.index[-1]
    latest = scored.loc[last_dt]
    prev_1w = valid_scores.iloc[-6] if len(valid_scores) >= 6 else latest
    prev_1m = valid_scores.iloc[-22] if len(valid_scores) >= 22 else latest

    score_now = _clean_float(latest["growth_macro_score"], 1) or 50.0
    score_1w_delta = _clean_float(score_now - float(prev_1w["growth_macro_score"]), 1)
    score_1m_delta = _clean_float(score_now - float(prev_1m["growth_macro_score"]), 1)
    sahm_now = _clean_float(latest["sahm"], 2)
    regime = classify_regime(score_now, sahm_value=sahm_now, config=cfg)

    # Checklist de Alerta Temprana Tech (4 condiciones)
    qqq_dist = _clean_float(latest["qqq_dist_sma200_pct"], 1)
    smh_dist = _clean_float(latest["smh_dist_sma200_pct"], 1)
    vxn_now = _clean_float(latest["vxn"], 1)
    liq_3m_pct = _clean_float(latest["net_liq_roc_3m_pct"], 1)
    dfii10_shock = _clean_float(latest["dfii10_max_shock_bp"], 0)
    iwf_iwd_now = _clean_float(latest["iwf_iwd_2y_minmax"], 0)
    div_now = bool(latest["breadth_bearish_divergence"]) if pd.notna(latest["breadth_bearish_divergence"]) else False

    early_warning = {
        "active": bool(latest["tech_early_warning"]),
        "conditions_met": int(latest["ew_conditions_met"]),
        "required": int(ew_cfg.get("min_conditions", 3)),
        "badge_label": "Riesgo de Techo Tech",
        "conditions": [
            {
                "id": "extension",
                "label": f"QQQ > +{ew_cfg['qqq_sma200_pct']:.0f}% o SMH > +{ew_cfg['smh_sma200_pct']:.0f}% sobre SMA 200",
                "met": bool(latest["ew_cond_1_extension"]),
                "reading": f"QQQ {_fmt_signed(qqq_dist, '%')} · SMH {_fmt_signed(smh_dist, '%')}",
            },
            {
                "id": "vxn",
                "label": f"^VXN < {ew_cfg['vxn_below']:.1f} (complacencia Nasdaq)",
                "met": bool(latest["ew_cond_2_vxn"]),
                "reading": f"^VXN {vxn_now:.1f}" if vxn_now is not None else "N/D",
            },
            {
                "id": "liq_rates",
                "label": f"Liquidez neta 3M < 0% o DFII10 > +{ew_cfg['dfii10_rise_bp']:.0f} pb (1-3M)",
                "met": bool(latest["ew_cond_3_liq_rates"]),
                "reading": f"Liq 3M {_fmt_signed(liq_3m_pct, '%')} · DFII10 {_fmt_signed(dfii10_shock, ' pb', 0)}",
            },
            {
                "id": "breadth_growth",
                "label": f"Divergencia bajista QQQE/QQQ o IWF/IWD > {ew_cfg['iwf_iwd_above']:.0f}",
                "met": bool(latest["ew_cond_4_breadth_growth"]),
                "reading": f"Div: {'Sí' if div_now else 'No'} · IWF/IWD {iwf_iwd_now:.0f}/100" if iwf_iwd_now is not None else "N/D",
            },
        ],
    }

    # --- Preparación de series específicas por módulo ---

    # Módulo 1: Liquidez Neta (5 años)
    m1_score = _clean_float(latest["score_liquidity"], 1)
    net_liq_now = _clean_float(latest["net_liquidity_bn"], 0)
    net_liq_chg_bn = _clean_float(latest["net_liq_chg_3m_bn"], 0)
    nfci_now = _clean_float(latest["nfci"], 2)
    m1_note = (
        f"Liquidez neta de la Fed en ${net_liq_now:,.0f}B ({_fmt_signed(liq_3m_pct, '%')} en 3M) y NFCI en {_fmt_signed(nfci_now, '', 2)}. "
        + (
            "La liquidez se contrae en 3 meses: viento en contra directo para múltiplos tech."
            if (liq_3m_pct is not None and liq_3m_pct < 0)
            else "Liquidez estable o expansiva en 3 meses: sin drenaje agudo de balance por ahora."
        )
    ) if net_liq_now is not None else "Datos de liquidez en actualización."

    module_1 = {
        "id": "liquidity",
        "number": 1,
        "title": "Liquidez Neta y Condiciones Financieras",
        "subtitle": "WALCL − TGA − RRP (miles de millones USD) · tasa de cambio 3M y Chicago Fed NFCI · 5 años",
        "weight": weights["liquidity"],
        "score": m1_score,
        "kpis": {
            "net_liquidity_bn": net_liq_now,
            "net_liq_roc_3m_pct": liq_3m_pct,
            "net_liq_chg_3m_bn": net_liq_chg_bn,
            "nfci": nfci_now,
            "walcl_bn": _clean_float(latest["walcl_bn"], 0),
            "tga_bn": _clean_float(latest["tga_bn"], 0),
            "rrp_bn": _clean_float(latest["rrp_bn"], 0),
        },
        "interpretation": m1_note,
        "series": _series_to_points(
            scored,
            {
                "net_liquidity_bn": "net_liquidity_bn",
                "roc_3m_pct": "net_liq_roc_3m_pct",
                "nfci": "nfci",
                "score": "score_liquidity",
            },
            years=5,
            stride=2,
            digits=2,
        ),
    }

    # Módulo 2: Tipos Reales y Ciclo Económico (5 años)
    m2_score = _clean_float(latest["score_real_rates"], 1)
    dfii10_now = _clean_float(latest["dfii10"], 2)
    dfii10_1m = _clean_float(latest["dfii10_chg_1m_bp"], 0)
    dfii10_3m = _clean_float(latest["dfii10_chg_3m_bp"], 0)
    t10y2y_now = _clean_float(latest["t10y2y"], 2)
    cycle_now = str(latest["cycle_label"])

    if cycle_now == "Alerta Recesión":
        m2_note = (
            f"Regla de Sahm en {sahm_now:.2f} (>= 0.50): alerta de recesión activa. "
            f"DFII10 en {dfii10_now:.2f}% ({_fmt_signed(dfii10_3m, ' pb', 0)} en 3M); si se compra debilidad, espaciar tramos varias semanas."
        )
    elif cycle_now == "Presión de Tipos":
        m2_note = (
            f"DFII10 en {dfii10_now:.2f}% con repunte rápido ({_fmt_signed(dfii10_1m, ' pb', 0)} en 1M, {_fmt_signed(dfii10_3m, ' pb', 0)} en 3M > +35 pb): "
            "presión directa sobre valoraciones de duración larga (growth/software) aunque el empleo aguante."
        )
    else:
        m2_note = (
            f"Ciclo en Expansión (Sahm {sahm_now:.2f}, curva 10Y-2Y {_fmt_signed(t10y2y_now, '%', 2)}). "
            f"Tipo real a 10 años en {dfii10_now:.2f}% ({_fmt_signed(dfii10_1m, ' pb', 0)} en 1M, {_fmt_signed(dfii10_3m, ' pb', 0)} en 3M): sin choque brusco de tipos reales."
        )

    module_2 = {
        "id": "real_rates",
        "number": 2,
        "title": "Tipos Reales y Ciclo Económico",
        "subtitle": "TIPS 10 años (DFII10), variación en pb a 1M/3M, curva 10Y-2Y (T10Y2Y) y Regla de Sahm · 5 años",
        "weight": weights["real_rates"],
        "score": m2_score,
        "cycle_label": cycle_now,
        "kpis": {
            "dfii10": dfii10_now,
            "dfii10_chg_1m_bp": dfii10_1m,
            "dfii10_chg_3m_bp": dfii10_3m,
            "t10y2y": t10y2y_now,
            "sahm": sahm_now,
        },
        "interpretation": m2_note,
        "series": _series_to_points(
            scored,
            {
                "dfii10": "dfii10",
                "chg_3m_bp": "dfii10_chg_3m_bp",
                "t10y2y": "t10y2y",
                "sahm": "sahm",
                "score": "score_real_rates",
            },
            years=5,
            stride=2,
            digits=2,
        ),
    }

    # Módulo 3: Sobreextensión Tech, Semis y Factor Growth (5 años)
    m3_score = _clean_float(latest["score_tech_extension"], 1)
    if (qqq_dist is not None and qqq_dist > 16) or (smh_dist is not None and smh_dist > 25) or (iwf_iwd_now is not None and iwf_iwd_now > 85):
        m3_note = (
            f"Sobrecalentamiento tech: QQQ {_fmt_signed(qqq_dist, '%')} y SMH {_fmt_signed(smh_dist, '%')} vs SMA 200; "
            f"factor Growth/Value (IWF/IWD) en {iwf_iwd_now:.0f}/100. Zona histórica de asimetría desfavorable para perseguir precio."
        )
    elif (qqq_dist is not None and qqq_dist < -10) or (smh_dist is not None and smh_dist < -15):
        m3_note = (
            f"Capitulación técnica: QQQ {_fmt_signed(qqq_dist, '%')} y SMH {_fmt_signed(smh_dist, '%')} bajo su SMA 200. "
            "Desviaciones de este calibre suelen abrir ventanas atractivas de compra escalonada."
        )
    else:
        m3_note = (
            f"QQQ {_fmt_signed(qqq_dist, '%')} y SMH {_fmt_signed(smh_dist, '%')} respecto a su SMA 200; "
            f"ratio Growth/Value (IWF/IWD) en {iwf_iwd_now:.0f} de 100 (rango 2 años). Sin extremos de euforia ni capitulación."
        )

    module_3 = {
        "id": "tech_extension",
        "number": 3,
        "title": "Sobreextensión Tech, Semis y Factor Growth",
        "subtitle": "distancia porcentual de QQQ y SMH frente a su SMA 200 · IWF/IWD normalizado 0–100 (2 años) · 5 años",
        "weight": weights["tech_extension"],
        "score": m3_score,
        "kpis": {
            "qqq_dist_sma200_pct": qqq_dist,
            "smh_dist_sma200_pct": smh_dist,
            "iwf_iwd_2y_minmax": iwf_iwd_now,
            "qqq_price": _clean_float(latest["price_qqq"], 2),
            "smh_price": _clean_float(latest["price_smh"], 2),
        },
        "interpretation": m3_note,
        "series": _series_to_points(
            scored,
            {
                "qqq_dist": "qqq_dist_sma200_pct",
                "smh_dist": "smh_dist_sma200_pct",
                "iwf_iwd_0_100": "iwf_iwd_2y_minmax",
                "score": "score_tech_extension",
            },
            years=5,
            stride=2,
            digits=2,
        ),
    }

    # Módulo 4: Amplitud de Mercado — "How Many Stocks Take Part" (5 años exactos, base 100 al inicio)
    m4_score = _clean_float(latest["score_market_breadth"], 1)
    cutoff_5y = scored.index[-1] - pd.DateOffset(years=5)
    b5 = scored[scored.index >= cutoff_5y].copy()

    rsp_base = b5["rsp_spy_ratio"].dropna().iloc[0] if not b5["rsp_spy_ratio"].dropna().empty else 1.0
    qqqe_base = b5["qqqe_qqq_ratio"].dropna().iloc[0] if not b5["qqqe_qqq_ratio"].dropna().empty else 1.0
    b5["rsp_spy_base100"] = (b5["rsp_spy_ratio"] / rsp_base) * 100.0
    b5["rsp_spy_sma200_base100"] = (b5["rsp_spy_sma200"] / rsp_base) * 100.0
    b5["qqqe_qqq_base100"] = (b5["qqqe_qqq_ratio"] / qqqe_base) * 100.0
    b5["qqqe_qqq_sma200_base100"] = (b5["qqqe_qqq_sma200"] / qqqe_base) * 100.0

    pct_sec_now = _clean_float(latest["pct_sectors_above_sma200"], 0)
    sec_above_n = int(latest["sectors_above_sma200_count"]) if pd.notna(latest["sectors_above_sma200_count"]) else 0
    sec_valid_n = int(latest["sectors_valid_count"]) if pd.notna(latest["sectors_valid_count"]) else 11
    rsp_3m = _clean_float(latest["rsp_spy_roc_3m_pct"], 1)
    qqqe_3m = _clean_float(latest["qqqe_qqq_roc_3m_pct"], 1)

    if div_now:
        m4_note = (
            f"Divergencia bajista activa: QQQ cerca de máximos de 3 meses mientras QQQE/QQQ se debilita ({_fmt_signed(qqqe_3m, '%')} en 3M). "
            f"Sectores sobre SMA 200: {pct_sec_now:.0f}% ({sec_above_n} de {sec_valid_n}). Pocos valores sostienen el índice."
        )
    elif pct_sec_now is not None and pct_sec_now < 20:
        m4_note = (
            f"Amplitud lavada: solo {pct_sec_now:.0f}% de sectores ({sec_above_n}/{sec_valid_n}) sobre su SMA 200 (banda verde <20%). "
            "Zona histórica para iniciar el primer tramo de compra."
        )
    elif pct_sec_now is not None and pct_sec_now > 80:
        m4_note = (
            f"Participación muy extendida: {pct_sec_now:.0f}% de sectores ({sec_above_n}/{sec_valid_n}) sobre su SMA 200 (banda roja >80%). "
            f"RSP/SPY en 3M: {_fmt_signed(rsp_3m, '%')}."
        )
    else:
        m4_note = (
            f"Hoy {pct_sec_now:.0f}% de los sectores ({sec_above_n}/{sec_valid_n}) cotizan sobre su SMA 200. "
            f"RSP/SPY 3M: {_fmt_signed(rsp_3m, '%')} · QQQE/QQQ 3M: {_fmt_signed(qqqe_3m, '%')}. Banda verde (<20%) = lavado; banda roja (>80%) = euforia."
        )

    module_4 = {
        "id": "market_breadth",
        "number": 4,
        "title": "How Many Stocks Take Part",
        "subtitle": "5 años, mismo eje · arriba: RSP/SPY y QQQE/QQQ (base 100) con SMA 200 · abajo: % de los 11 sectores sobre SMA 200",
        "weight": weights["market_breadth"],
        "score": m4_score,
        "bearish_divergence": div_now,
        "kpis": {
            "pct_sectors_above_sma200": pct_sec_now,
            "sectors_above": sec_above_n,
            "sectors_total": sec_valid_n,
            "rsp_spy_roc_3m_pct": rsp_3m,
            "qqqe_qqq_roc_3m_pct": qqqe_3m,
            "rsp_spy_base100": _clean_float(b5["rsp_spy_base100"].iloc[-1], 1),
            "qqqe_qqq_base100": _clean_float(b5["qqqe_qqq_base100"].iloc[-1], 1),
        },
        "interpretation": m4_note,
        "series": _series_to_points(
            b5,
            {
                "rsp_spy": "rsp_spy_base100",
                "rsp_spy_sma200": "rsp_spy_sma200_base100",
                "qqqe_qqq": "qqqe_qqq_base100",
                "qqqe_qqq_sma200": "qqqe_qqq_sma200_base100",
                "pct_sectors": "pct_sectors_above_sma200",
            },
            years=None,
            stride=2,
            digits=2,
        ),
    }

    # Módulo 5: Volatilidad Nasdaq y Estructura Temporal (5 años)
    m5_score = _clean_float(latest["score_volatility"], 1)
    term_now = _clean_float(latest["vix_term_ratio"], 2)
    vix_now = _clean_float(latest["vix"], 1)
    vix3m_now = _clean_float(latest["vix3m"], 1)

    if (vxn_now is not None and vxn_now < 17.0) and (term_now is not None and term_now < 0.85):
        m5_note = (
            f"Complacencia elevada: ^VXN en {vxn_now:.1f} (< 17) y ^VIX/^VIX3M en {term_now:.2f} (< 0.85). "
            "Cobertura barata o buen entorno para recortar posiciones muy extendidas."
        )
    elif (vxn_now is not None and vxn_now > 32.0) and (term_now is not None and term_now > 1.0):
        m5_note = (
            f"Capitulación de volatilidad: ^VXN en {vxn_now:.1f} (> 32) con curva en backwardation (^VIX/^VIX3M = {term_now:.2f} > 1.0). "
            "Pánico agudo típico de suelos tácticos en Nasdaq."
        )
    elif term_now is not None and term_now > 1.0:
        m5_note = (
            f"Estructura temporal invertida (^VIX/^VIX3M = {term_now:.2f} > 1.0, backwardation) con ^VXN en {vxn_now:.1f}. "
            "Estrés a corto plazo elevado: evitar ventas emocionales."
        )
    else:
        m5_note = (
            f"^VXN en {vxn_now:.1f} y estructura temporal ^VIX/^VIX3M en {term_now:.2f} (contango normal). "
            "Complacencia extrema bajo ^VXN < 17 y ratio < 0.85; capitulación sobre ^VXN > 32 y backwardation (> 1.0)."
        )

    module_5 = {
        "id": "volatility",
        "number": 5,
        "title": "Volatilidad Nasdaq y Estructura Temporal",
        "subtitle": "volatilidad implícita del Nasdaq-100 (^VXN) y curva ^VIX / ^VIX3M · 5 años",
        "weight": weights["volatility"],
        "score": m5_score,
        "kpis": {
            "vxn": vxn_now,
            "vix": vix_now,
            "vix3m": vix3m_now,
            "vix_term_ratio": term_now,
        },
        "interpretation": m5_note,
        "series": _series_to_points(
            scored,
            {
                "vxn": "vxn",
                "vix_term_ratio": "vix_term_ratio",
                "score": "score_volatility",
            },
            years=5,
            stride=2,
            digits=3,
        ),
    }

    # Módulo 6: Precio del Riesgo — "The Price of Risk" (tarjetas HY OAS y BBB OAS + sparkline 5 años)
    m6_score = _clean_float(latest["score_price_of_risk"], 1)
    hy_now = _clean_float(latest["hy_oas_bp"], 0)
    hy_1m = _clean_float(latest["hy_chg_1m_bp"], 0)
    hy_3m = _clean_float(latest["hy_chg_3m_bp"], 0)
    hy_pct = _clean_float(latest["hy_pct_10y"], 0)
    hy_med = _clean_float(latest["hy_median_hist_bp"], 0)

    bbb_now = _clean_float(latest["bbb_oas_bp"], 0)
    bbb_1m = _clean_float(latest["bbb_chg_1m_bp"], 0)
    bbb_3m = _clean_float(latest["bbb_chg_3m_bp"], 0)
    bbb_pct = _clean_float(latest["bbb_pct_10y"], 0)
    bbb_med = _clean_float(latest["bbb_median_hist_bp"], 0)

    credit_buy_now = bool(latest["credit_priority_buy"]) if pd.notna(latest["credit_priority_buy"]) else False
    is_limited_csv = bool(metadata.get("credit_history", {}).get("is_limited_csv_window", False))
    credit_window_label = "3 años (CSV público FRED)" if is_limited_csv else "10 años (FRED API)"

    def _credit_status(val: float | None, buy_th: float, tight_th: float) -> dict[str, str]:
        if val is None:
            return {"level": "neutral", "text": "sin datos"}
        if val > buy_th:
            return {"level": "buy", "text": "amplio: estrés — alerta prioritaria de compra"}
        if val >= buy_th * 0.88:
            return {"level": "watch", "text": "ensanchándose: vigilar oportunidad de crédito"}
        if val <= tight_th:
            return {"level": "tight", "text": "estrecho: apetito elevado / complacencia"}
        return {"level": "normal", "text": "normal"}

    hy_status = _credit_status(hy_now, float(cfg["thresholds"]["hy_priority_buy_bp"]), 320.0)
    bbb_status = _credit_status(bbb_now, float(cfg["thresholds"]["bbb_priority_buy_bp"]), 95.0)

    m6_note = (
        f"HY OAS en {hy_now:.0f} bp y BBB OAS en {bbb_now:.0f} bp. "
        + (
            "ALERTA PRIORITARIA DE COMPRA ACTIVADA (HY > 500 bp o BBB > 130 bp): el crédito ofrece una ventana de entrada histórica."
            if credit_buy_now
            else "Spreads de crédito contenidos: peso reducido (10%) para no frenar recortes en techos tech; alerta de compra si HY > 500 bp o BBB > 130 bp."
        )
    ) if (hy_now is not None and bbb_now is not None) else "Datos de crédito OAS no disponibles."

    module_6 = {
        "id": "price_of_risk",
        "number": 6,
        "title": "The Price of Risk",
        "subtitle": f"ICE BofA option-adjusted spreads (FRED) · percentil sobre {credit_window_label} · sparkline 5 años",
        "weight": weights["price_of_risk"],
        "score": m6_score,
        "priority_buy_alert": credit_buy_now,
        "window_label": credit_window_label,
        "is_limited_csv_window": is_limited_csv,
        "hy": {
            "label": "US High Yield (BAMLH0A0HYM2)",
            "value_bp": hy_now,
            "chg_1m_bp": hy_1m,
            "chg_3m_bp": hy_3m,
            "percentile": hy_pct,
            "tighter_than_pct": _clean_float(100.0 - hy_pct, 0) if hy_pct is not None else None,
            "median_bp": hy_med,
            "buy_threshold_bp": float(cfg["thresholds"]["hy_priority_buy_bp"]),
            "status": hy_status,
            "series": _series_to_points(
                scored.dropna(subset=["hy_oas_bp"]),
                {"value_bp": "hy_oas_bp"},
                years=5,
                stride=2,
                digits=1,
            ),
        },
        "bbb": {
            "label": "US BBB Investment Grade (BAMLC0A4CBBB)",
            "value_bp": bbb_now,
            "chg_1m_bp": bbb_1m,
            "chg_3m_bp": bbb_3m,
            "percentile": bbb_pct,
            "tighter_than_pct": _clean_float(100.0 - bbb_pct, 0) if bbb_pct is not None else None,
            "median_bp": bbb_med,
            "buy_threshold_bp": float(cfg["thresholds"]["bbb_priority_buy_bp"]),
            "status": bbb_status,
            "series": _series_to_points(
                scored.dropna(subset=["bbb_oas_bp"]),
                {"value_bp": "bbb_oas_bp"},
                years=5,
                stride=2,
                digits=1,
            ),
        },
        "interpretation": m6_note,
    }

    # Módulo 7: Cíclicos vs. Defensivos — "Cyclicals Against Defensives" (historia larga 2006+)
    m7_score = _clean_float(latest["score_cyclicals_defensives"], 1)
    cyc_raw_now = _clean_float(latest["cyc_def_raw_0_100"], 0)
    cyc_ma5_now = _clean_float(latest["cyc_def_ma5"], 0)
    xlk_xlp_pct = _clean_float(latest["xlk_xlp_2y_pct"], 0)

    if cyc_ma5_now is not None and cyc_ma5_now >= 80:
        cyc_zone = "en banda roja (estirado: zona de recortar cíclicos hacia defensivos)"
    elif cyc_ma5_now is not None and cyc_ma5_now <= 20:
        cyc_zone = "en banda verde (lavado: zona histórica de comprar cíclicos y riesgo)"
    else:
        cyc_zone = "en zona intermedia"

    m7_note = (
        f"Hoy {cyc_raw_now:.0f} de 100 (línea 5 días: {cyc_ma5_now:.0f}): {cyc_zone}. "
        f"Por debajo de 20 ha sido zona de compra; por encima de 80, zona de recorte. "
        f"XLK / XLP (Tech vs Consumo Básico) en percentil {xlk_xlp_pct:.0f}% de 2 años."
    ) if (cyc_raw_now is not None and cyc_ma5_now is not None and xlk_xlp_pct is not None) else "Datos insuficientes."

    module_7 = {
        "id": "cyclicals_defensives",
        "number": 7,
        "title": "Cyclicals Against Defensives",
        "subtitle": "cesta equiponderada cíclicos (XLY, XLI, XLF, XLK, XLB) frente a defensivos (XLP, XLU, XLV) en su rango móvil de 2 años, 0 a 100 · media 5 días",
        "weight": weights["cyclicals_defensives"],
        "score": m7_score,
        "kpis": {
            "raw_0_100": cyc_raw_now,
            "ma5_0_100": cyc_ma5_now,
            "xlk_xlp_2y_pct": xlk_xlp_pct,
        },
        "interpretation": m7_note,
        "series": _series_to_points(
            scored.dropna(subset=["cyc_def_ma5"]),
            {
                "ma5": "cyc_def_ma5",
                "raw": "cyc_def_raw_0_100",
                "xlk_xlp_pct": "xlk_xlp_2y_pct",
            },
            years=None,  # Historia completa desde 2006 como en la captura de referencia
            stride=5,
            digits=1,
        ),
    }

    return {
        "as_of_date": pd.Timestamp(last_dt).strftime("%Y-%m-%d"),
        "metadata": metadata,
        "summary": {
            "growth_macro_score": score_now,
            "score_1w_delta": score_1w_delta,
            "score_1m_delta": score_1m_delta,
            "regime": regime,
            "early_warning_tech": early_warning,
            "credit_priority_buy": credit_buy_now,
            "sahm": sahm_now,
        },
        "modules": [
            module_1,
            module_2,
            module_3,
            module_4,
            module_5,
            module_6,
            module_7,
        ],
    }


def build_backtest_payload(
    scored: pd.DataFrame,
    ticker: str = "QQQ",
    years: int = 10,
) -> dict[str, Any]:
    """Genera la serie de backtest histórico (10 años) con señales rojas (>80 o Alerta Tech) y verdes (<20)."""
    clean_ticker = ticker.upper().strip()
    if clean_ticker not in ("QQQ", "SMH", "SPY"):
        raise ValueError("El ticker de backtest debe ser QQQ, SMH o SPY.")

    price_col = f"price_{clean_ticker.lower()}"
    df = scored.dropna(subset=[price_col, "growth_macro_score"]).copy()
    if df.empty:
        raise ValueError(f"No hay historial disponible para {clean_ticker}.")

    # Retornos futuros descriptivos (solo para estadísticas de evaluación ex-post, nunca usados en el score)
    df["fwd_3m_pct"] = (df[price_col].shift(-63) / df[price_col] - 1.0) * 100.0
    df["fwd_6m_pct"] = (df[price_col].shift(-126) / df[price_col] - 1.0) * 100.0

    cutoff = df.index[-1] - pd.DateOffset(years=years)
    window = df[df.index >= cutoff].copy()

    # Clasificación diaria de señales
    is_red_score = window["growth_macro_score"] >= 80.0
    is_tech_alert = window["tech_early_warning"].fillna(False)
    is_red = is_red_score | is_tech_alert
    is_green = window["growth_macro_score"] < 20.0

    # Para el gráfico (fluido en Recharts): conservar 1 punto cada 3 sesiones + TODOS los cambios de señal + último día
    signal_code = np.where(is_red, 2, np.where(is_green, 1, 0))
    sig_changed = pd.Series(signal_code, index=window.index).diff().fillna(0) != 0
    keep_mask = np.zeros(len(window), dtype=bool)
    keep_mask[::3] = True
    keep_mask[-1] = True
    keep_mask |= sig_changed.to_numpy()
    # También preservar cualquier punto extremo que no haya quedado cubierto
    keep_mask |= (is_red.to_numpy() & (np.arange(len(window)) % 2 == 0))
    keep_mask |= (is_green.to_numpy() & (np.arange(len(window)) % 2 == 0))

    sampled = window.iloc[keep_mask]
    points: list[dict[str, Any]] = []
    for dt, row in sampled.iterrows():
        score_v = _clean_float(row["growth_macro_score"], 1)
        price_v = _clean_float(row[price_col], 2)
        tech_v = bool(row["tech_early_warning"]) if pd.notna(row["tech_early_warning"]) else False
        red_v = (score_v is not None and score_v >= 80.0) or tech_v
        green_v = score_v is not None and score_v < 20.0
        points.append(
            {
                "date": pd.Timestamp(dt).strftime("%Y-%m-%d"),
                "price": price_v,
                "score": score_v,
                "tech_early_warning": tech_v,
                "signal": "red" if red_v else ("green" if green_v else None),
                "red_marker": price_v if red_v else None,
                "green_marker": price_v if green_v else None,
            }
        )

    def _zone_stats(mask: pd.Series) -> dict[str, Any]:
        sub = window[mask]
        # Contar episodios diferenciados (separados por al menos 15 sesiones)
        episodes = 0
        last_idx = -999
        positions = np.flatnonzero(mask.to_numpy())
        for pos in positions:
            if pos - last_idx >= 15:
                episodes += 1
            last_idx = int(pos)
        return {
            "days": int(mask.sum()),
            "episodes": episodes,
            "avg_fwd_3m_pct": _clean_float(sub["fwd_3m_pct"].mean(), 1) if not sub["fwd_3m_pct"].dropna().empty else None,
            "avg_fwd_6m_pct": _clean_float(sub["fwd_6m_pct"].mean(), 1) if not sub["fwd_6m_pct"].dropna().empty else None,
        }

    return {
        "ticker": clean_ticker,
        "years": years,
        "start_date": window.index[0].strftime("%Y-%m-%d"),
        "end_date": window.index[-1].strftime("%Y-%m-%d"),
        "stats": {
            "red_zone": _zone_stats(is_red),
            "euphoria_score_only": _zone_stats(is_red_score),
            "tech_early_warning": _zone_stats(is_tech_alert),
            "green_zone": _zone_stats(is_green),
            "baseline": _zone_stats(pd.Series(True, index=window.index)),
        },
        "series": points,
    }
