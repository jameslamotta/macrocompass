"""Configuración centralizada de MacroCompass (.env + config/weights.yaml)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "weights.yaml"
DEFAULT_DB_PATH = BACKEND_DIR / "data" / "macrocompass.db"

# Cargar variables de entorno desde raíz del proyecto y/o backend/
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env", override=False)

FRED_SERIES: tuple[str, ...] = (
    "WALCL",
    "WTREGEN",
    "RRPONTSYD",
    "NFCI",
    "DFII10",
    "T10Y2Y",
    "SAHMREALTIME",
    "BAMLH0A0HYM2",
    "BAMLC0A4CBBB",
)

SECTOR_ETFS: tuple[str, ...] = (
    "XLK",
    "XLF",
    "XLV",
    "XLY",
    "XLP",
    "XLE",
    "XLI",
    "XLB",
    "XLU",
    "XLRE",
    "XLC",
)

CYCLICAL_ETFS: tuple[str, ...] = ("XLY", "XLI", "XLF", "XLK", "XLB")
DEFENSIVE_ETFS: tuple[str, ...] = ("XLP", "XLU", "XLV")

EQUITY_ETFS: tuple[str, ...] = (
    "QQQ",
    "SMH",
    "SPY",
    "IWF",
    "IWD",
    "RSP",
    "QQQE",
    *SECTOR_ETFS,
)

VOL_INDICES: tuple[str, ...] = ("^VXN", "^VIX", "^VIX3M")

ALL_MARKET_TICKERS: tuple[str, ...] = (*EQUITY_ETFS, *VOL_INDICES)


@lru_cache(maxsize=1)
def load_weights_config(path: Path | None = None) -> dict[str, Any]:
    """Lee y valida config/weights.yaml."""
    cfg_path = path or CONFIG_PATH
    with open(cfg_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or "weights" not in data:
        raise ValueError(f"Archivo de configuración inválido: {cfg_path}")
    return data


def get_env_settings() -> dict[str, Any]:
    """Devuelve credenciales y opciones operativas desde variables de entorno."""
    return {
        "fred_api_key": os.getenv("FRED_API_KEY", "").strip() or None,
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or None,
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", "").strip() or None,
        "smtp_host": os.getenv("SMTP_HOST", "").strip() or None,
        "smtp_port": int(os.getenv("SMTP_PORT", "587") or "587"),
        "smtp_user": os.getenv("SMTP_USER", "").strip() or None,
        "smtp_pass": os.getenv("SMTP_PASS", "").strip() or None,
        "alert_email_from": os.getenv("ALERT_EMAIL_FROM", "").strip() or None,
        "alert_email_to": os.getenv("ALERT_EMAIL_TO", "").strip() or None,
        "cache_ttl_hours": float(os.getenv("CACHE_TTL_HOURS", "4") or "4"),
        "db_path": Path(os.getenv("MACROCOMPASS_DB_PATH", str(DEFAULT_DB_PATH))),
    }
