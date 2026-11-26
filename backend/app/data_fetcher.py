"""Motor de ingesta de datos (FRED API + fallback CSV público y Yahoo Finance) con alineación causal."""

from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from app.config import (
    ALL_MARKET_TICKERS,
    EQUITY_ETFS,
    FRED_SERIES,
    VOL_INDICES,
    get_env_settings,
    load_weights_config,
)
from app.database import MacroDatabase

logger = logging.getLogger(__name__)

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
DEFAULT_START_DATE = "2006-01-01"


def fetch_fred_csv(series_id: str, timeout: int = 15) -> pd.Series:
    """Descarga una serie de FRED mediante su endpoint CSV público sin necesidad de API Key."""
    url = FRED_CSV_URL.format(series_id=series_id)
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "curl/8.5.0", "Accept": "text/csv,*/*"},
            )
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
            if df.shape[1] < 2:
                raise ValueError(f"Respuesta CSV inesperada de FRED para {series_id}")
            date_col = df.columns[0]
            val_col = df.columns[1]
            dates = pd.to_datetime(df[date_col], errors="coerce")
            vals = pd.to_numeric(df[val_col], errors="coerce")
            series = pd.Series(vals.values, index=dates, name=series_id, dtype=float)
            series = series[~series.index.isna()].dropna().sort_index()
            series = series[~series.index.duplicated(keep="last")]
            return series
        except Exception as exc:
            last_exc = exc
            logger.warning("Intento %d fallido descargando FRED %s: %s", attempt + 1, series_id, exc)
    assert last_exc is not None
    raise last_exc


def fetch_fred_series(
    series_id: str,
    api_key: str | None = None,
    start_date: str = DEFAULT_START_DATE,
) -> tuple[pd.Series, str]:
    """Obtiene una serie de FRED usando fredapi si hay clave y haciendo fallback automático al CSV público."""
    if api_key:
        try:
            from fredapi import Fred

            fred = Fred(api_key=api_key)
            raw = fred.get_series(series_id, observation_start=start_date)
            series = pd.to_numeric(raw, errors="coerce").dropna().sort_index()
            series.index = pd.to_datetime(series.index)
            series.name = series_id
            series = series[~series.index.duplicated(keep="last")]
            if not series.empty:
                return series, "fred_api"
        except Exception as exc:
            logger.warning(
                "FRED API falló para %s (%s); usando fallback CSV público.",
                series_id,
                exc,
            )

    series = fetch_fred_csv(series_id)
    series = series[series.index >= pd.Timestamp(start_date)]
    return series, "fred_csv_fallback"


def _extract_close_from_yf(df: pd.DataFrame, ticker: str) -> pd.Series:
    """Extrae de forma segura la serie de cierre de un DataFrame de yfinance (single o MultiIndex)."""
    if df is None or df.empty:
        return pd.Series(dtype=float, name=ticker)

    if isinstance(df.columns, pd.MultiIndex):
        # yfinance >= 0.2.50 devuelve (Price, Ticker) o (Ticker, Price)
        if ticker in df.columns.get_level_values(-1):
            sub = df.xs(ticker, axis=1, level=-1)
        elif ticker in df.columns.get_level_values(0):
            sub = df.xs(ticker, axis=1, level=0)
        else:
            return pd.Series(dtype=float, name=ticker)
        col = "Close" if "Close" in sub.columns else ("Adj Close" if "Adj Close" in sub.columns else sub.columns[0])
        s = sub[col]
    else:
        col = "Close" if "Close" in df.columns else ("Adj Close" if "Adj Close" in df.columns else df.columns[0])
        s = df[col]

    s = pd.to_numeric(s, errors="coerce").dropna().sort_index()
    idx = pd.to_datetime(s.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    s.index = idx.normalize()
    s = s[~s.index.duplicated(keep="last")]
    s.name = ticker
    return s


def fetch_yfinance_tickers(
    tickers: tuple[str, ...],
    start_date: str = DEFAULT_START_DATE,
    auto_adjust: bool = True,
) -> dict[str, pd.Series]:
    """Descarga precios históricos de Yahoo Finance con fallback por ticker individual."""
    results: dict[str, pd.Series] = {}
    if not tickers:
        return results

    try:
        batch = yf.download(
            list(tickers),
            start=start_date,
            auto_adjust=auto_adjust,
            progress=False,
            threads=True,
        )
        for t in tickers:
            s = _extract_close_from_yf(batch, t)
            if not s.empty:
                results[t] = s
    except Exception as exc:
        logger.warning("Descarga en lote de yfinance falló (%s); reintentando por ticker.", exc)

    # Fallback individual para tickers que hayan faltado en el lote
    for t in tickers:
        if t in results and not results[t].empty:
            continue
        try:
            single = yf.download(
                t,
                start=start_date,
                auto_adjust=auto_adjust,
                progress=False,
            )
            s = _extract_close_from_yf(single, t)
            if not s.empty:
                results[t] = s
        except Exception as exc:
            logger.error("Error descargando ticker %s desde yfinance: %s", t, exc)

    return results


def apply_publication_lag(
    series: pd.Series,
    unit: str = "business_days",
    lag: int = 0,
) -> pd.Series:
    """Desplaza el índice temporal hacia adelante según el retardo oficial de publicación.

    Garantiza que una serie macro solo está disponible en el calendario bursátil a partir
    de la fecha real en que el mercado pudo conocerla (sin look-ahead bias).
    """
    if series.empty:
        return series.copy()

    s = series.sort_index().copy()
    s.index = pd.to_datetime(s.index).normalize()
    if lag > 0:
        if unit == "business_days":
            s.index = s.index + pd.offsets.BDay(lag)
        elif unit == "calendar_days":
            s.index = s.index + pd.Timedelta(days=lag)
        else:
            raise ValueError(f"Unidad de lag no soportada: {unit}")
    s = s[~s.index.duplicated(keep="last")]
    return s


def align_series_to_calendar(
    series: pd.Series,
    trading_calendar: pd.DatetimeIndex,
    lag_spec: dict[str, Any] | None = None,
) -> pd.Series:
    """Alinea una serie de cualquier frecuencia al calendario bursátil usando solo ffill() causal.

    Nunca utiliza bfill() ni observaciones posteriores a la fecha t.
    """
    if trading_calendar.empty:
        return pd.Series(dtype=float, name=series.name)
    if series.empty:
        return pd.Series(float("nan"), index=trading_calendar, name=series.name, dtype=float)

    unit = (lag_spec or {}).get("unit", "business_days")
    lag = int((lag_spec or {}).get("lag", 0))
    shifted = apply_publication_lag(series, unit=unit, lag=lag)

    union_idx = shifted.index.union(trading_calendar).sort_values()
    aligned = shifted.reindex(union_idx).ffill().reindex(trading_calendar)
    aligned.name = series.name
    return aligned


def align_all_to_trading_calendar(
    market_series: dict[str, pd.Series],
    fred_series: dict[str, pd.Series],
    publication_lags: dict[str, dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Construye el DataFrame maestro diario alineado al calendario de SPY/QQQ sin look-ahead bias."""
    ref_ticker = "SPY" if "SPY" in market_series and not market_series["SPY"].empty else "QQQ"
    if ref_ticker not in market_series or market_series[ref_ticker].empty:
        raise ValueError("No se encontraron datos de calendario maestro (SPY/QQQ).")

    calendar = pd.DatetimeIndex(sorted(market_series[ref_ticker].dropna().index.unique()))
    lags = publication_lags or {}
    columns: dict[str, pd.Series] = {}

    for ticker, s in market_series.items():
        # Para activos bursátiles usamos ffill() limitado para festivos locales sin mirar adelante
        columns[ticker] = align_series_to_calendar(s, calendar, lag_spec={"unit": "business_days", "lag": 0})

    for sid, s in fred_series.items():
        columns[sid] = align_series_to_calendar(s, calendar, lag_spec=lags.get(sid))

    df = pd.DataFrame(columns, index=calendar)
    df.index.name = "date"
    return df


class DataRepository:
    """Orquesta caché SQLite, refresco incremental y construcción del DataFrame alineado."""

    def __init__(self, db: MacroDatabase | None = None) -> None:
        self.env = get_env_settings()
        self.cfg = load_weights_config()
        self.db = db or MacroDatabase(self.env["db_path"])

    def _is_fresh(self, source: str, series_id: str, ttl_hours: float) -> bool:
        meta = self.db.get_meta(source, series_id)
        if not meta or meta["row_count"] <= 0:
            return False
        try:
            fetched = datetime.fromisoformat(meta["last_fetched_utc"])
        except ValueError:
            return False
        age = datetime.now(timezone.utc) - fetched
        return age < timedelta(hours=ttl_hours)

    def refresh_all(self, force: bool = False) -> dict[str, Any]:
        """Actualiza en SQLite las series de FRED y Yahoo Finance que estén caducadas o si force=True."""
        ttl = 0.0 if force else float(self.env["cache_ttl_hours"])
        api_key = self.env["fred_api_key"]

        fred_modes: dict[str, str] = {}
        refreshed_fred: list[str] = []
        errors: list[str] = []

        for sid in FRED_SERIES:
            if not force and self._is_fresh("fred", sid, ttl):
                meta = self.db.get_meta("fred", sid)
                fred_modes[sid] = meta["fetch_mode"] if meta else "cache"
                continue
            try:
                series, mode = fetch_fred_series(sid, api_key=api_key, start_date=DEFAULT_START_DATE)
                self.db.upsert_series("fred", sid, series, fetch_mode=mode)
                fred_modes[sid] = mode
                refreshed_fred.append(sid)
            except Exception as exc:
                logger.error("Error refrescando FRED %s: %s", sid, exc)
                errors.append(f"FRED:{sid}: {exc}")

        stale_equities = tuple(
            t for t in EQUITY_ETFS if force or not self._is_fresh("yfinance", t, ttl)
        )
        stale_vols = tuple(
            t for t in VOL_INDICES if force or not self._is_fresh("yfinance", t, ttl)
        )
        refreshed_yf: list[str] = []

        if stale_equities:
            fetched_eq = fetch_yfinance_tickers(stale_equities, start_date=DEFAULT_START_DATE, auto_adjust=True)
            for t, s in fetched_eq.items():
                self.db.upsert_series("yfinance", t, s, fetch_mode="yfinance_adj")
                refreshed_yf.append(t)
            for t in stale_equities:
                if t not in fetched_eq:
                    errors.append(f"YF:{t}: sin datos")

        if stale_vols:
            fetched_vol = fetch_yfinance_tickers(stale_vols, start_date=DEFAULT_START_DATE, auto_adjust=False)
            for t, s in fetched_vol.items():
                self.db.upsert_series("yfinance", t, s, fetch_mode="yfinance_spot")
                refreshed_yf.append(t)
            for t in stale_vols:
                if t not in fetched_vol:
                    errors.append(f"YF:{t}: sin datos")

        return {
            "refreshed_fred": refreshed_fred,
            "refreshed_yfinance": refreshed_yf,
            "fred_modes": fred_modes,
            "errors": errors,
        }

    def load_aligned_dataframe(self, refresh_if_stale: bool = True, force_refresh: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Devuelve el DataFrame maestro diario y metadatos de fuentes/frescura."""
        refresh_info = {"refreshed_fred": [], "refreshed_yfinance": [], "errors": []}
        if refresh_if_stale or force_refresh:
            refresh_info = self.refresh_all(force=force_refresh)

        market_data: dict[str, pd.Series] = {}
        for t in ALL_MARKET_TICKERS:
            market_data[t] = self.db.load_series("yfinance", t)

        fred_data: dict[str, pd.Series] = {}
        for sid in FRED_SERIES:
            fred_data[sid] = self.db.load_series("fred", sid)

        df = align_all_to_trading_calendar(
            market_series=market_data,
            fred_series=fred_data,
            publication_lags=self.cfg.get("publication_lags", {}),
        )

        meta_rows = self.db.get_all_meta()
        fred_meta = {m["series_id"]: m for m in meta_rows if m["source"] == "fred"}
        any_api = any(m.get("fetch_mode") == "fred_api" for m in fred_meta.values())
        any_csv = any(m.get("fetch_mode") == "fred_csv_fallback" for m in fred_meta.values())
        fred_source_mode = "fred_api" if (any_api and not any_csv) else ("mixed" if any_api else "fred_csv_fallback")

        hy_meta = fred_meta.get("BAMLH0A0HYM2", {})
        bbb_meta = fred_meta.get("BAMLC0A4CBBB", {})
        last_updated = max((m["last_fetched_utc"] for m in meta_rows), default=None)

        metadata = {
            "fred_source_mode": fred_source_mode,
            "last_fetched_utc": last_updated,
            "as_of_date": df.index[-1].strftime("%Y-%m-%d") if not df.empty else None,
            "credit_history": {
                "hy_min_date": hy_meta.get("min_date"),
                "bbb_min_date": bbb_meta.get("min_date"),
                "is_limited_csv_window": fred_source_mode != "fred_api",
            },
            "refresh_errors": refresh_info.get("errors", []),
        }
        return df, metadata
