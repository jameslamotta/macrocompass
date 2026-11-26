"""Capa de persistencia SQLite para cachear series históricas y registrar alertas."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from app.config import DEFAULT_DB_PATH


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS time_series (
    source TEXT NOT NULL,
    series_id TEXT NOT NULL,
    obs_date TEXT NOT NULL,
    value REAL NOT NULL,
    PRIMARY KEY (source, series_id, obs_date)
);

CREATE INDEX IF NOT EXISTS idx_time_series_lookup
    ON time_series (source, series_id, obs_date);

CREATE TABLE IF NOT EXISTS series_meta (
    source TEXT NOT NULL,
    series_id TEXT NOT NULL,
    last_fetched_utc TEXT NOT NULL,
    fetch_mode TEXT NOT NULL,
    min_date TEXT,
    max_date TEXT,
    row_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (source, series_id)
);

CREATE TABLE IF NOT EXISTS alert_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sent_at_utc TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    score REAL NOT NULL,
    regime_key TEXT NOT NULL,
    regime_label TEXT NOT NULL,
    tech_early_warning INTEGER NOT NULL,
    tech_conditions_met INTEGER NOT NULL,
    channels TEXT NOT NULL,
    message TEXT NOT NULL,
    dry_run INTEGER NOT NULL DEFAULT 0
);
"""


class MacroDatabase:
    """Gestor SQLite ligero con modo WAL para series macro y estado de alertas."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def upsert_series(
        self,
        source: str,
        series_id: str,
        series: pd.Series,
        fetch_mode: str,
    ) -> None:
        """Guarda o actualiza una serie histórica (DatetimeIndex -> float) en SQLite."""
        clean = pd.to_numeric(series, errors="coerce").dropna()
        now_iso = datetime.now(timezone.utc).isoformat()
        rows = [
            (source, series_id, pd.Timestamp(idx).strftime("%Y-%m-%d"), float(val))
            for idx, val in clean.items()
        ]
        min_date = rows[0][2] if rows else None
        max_date = rows[-1][2] if rows else None

        with self.connect() as conn:
            if rows:
                conn.executemany(
                    """
                    INSERT INTO time_series (source, series_id, obs_date, value)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(source, series_id, obs_date)
                    DO UPDATE SET value = excluded.value
                    """,
                    rows,
                )
            conn.execute(
                """
                INSERT INTO series_meta (
                    source, series_id, last_fetched_utc, fetch_mode, min_date, max_date, row_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, series_id)
                DO UPDATE SET
                    last_fetched_utc = excluded.last_fetched_utc,
                    fetch_mode = excluded.fetch_mode,
                    min_date = COALESCE(excluded.min_date, series_meta.min_date),
                    max_date = COALESCE(excluded.max_date, series_meta.max_date),
                    row_count = excluded.row_count
                """,
                (source, series_id, now_iso, fetch_mode, min_date, max_date, len(rows)),
            )

    def load_series(self, source: str, series_id: str) -> pd.Series:
        """Recupera una serie ordenada cronológicamente desde SQLite."""
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT obs_date, value
                FROM time_series
                WHERE source = ? AND series_id = ?
                ORDER BY obs_date ASC
                """,
                (source, series_id),
            ).fetchall()
        if not rows:
            return pd.Series(dtype=float, name=series_id)
        idx = pd.to_datetime([r["obs_date"] for r in rows])
        vals = [float(r["value"]) for r in rows]
        return pd.Series(vals, index=idx, name=series_id, dtype=float)

    def get_meta(self, source: str, series_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT source, series_id, last_fetched_utc, fetch_mode, min_date, max_date, row_count
                FROM series_meta
                WHERE source = ? AND series_id = ?
                """,
                (source, series_id),
            ).fetchone()
        return dict(row) if row is not None else None

    def get_all_meta(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT source, series_id, last_fetched_utc, fetch_mode, min_date, max_date, row_count
                FROM series_meta
                ORDER BY source, series_id
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def get_last_alert(self) -> dict[str, Any] | None:
        """Devuelve la última alerta real enviada (dry_run = 0)."""
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM alert_log
                WHERE dry_run = 0
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        return dict(row) if row is not None else None

    def record_alert(
        self,
        as_of_date: str,
        score: float,
        regime_key: str,
        regime_label: str,
        tech_early_warning: bool,
        tech_conditions_met: int,
        channels: list[str],
        message: str,
        dry_run: bool = False,
    ) -> int:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO alert_log (
                    sent_at_utc, as_of_date, score, regime_key, regime_label,
                    tech_early_warning, tech_conditions_met, channels, message, dry_run
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now_iso,
                    as_of_date,
                    float(score),
                    regime_key,
                    regime_label,
                    1 if tech_early_warning else 0,
                    int(tech_conditions_met),
                    ",".join(channels),
                    message,
                    1 if dry_run else 0,
                ),
            )
            return int(cur.lastrowid)
