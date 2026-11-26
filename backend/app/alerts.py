"""Sistema de alertas diarias al cierre de NY (Telegram Bot + Email SMTP opcional).

Solo envía notificación cuando cambia el régimen de temperatura o se activa la
Alerta Temprana Tech (transición de inactiva a activa), salvo que se pase --force.

Uso:
    python -m app.alerts --dry-run
    python -m app.alerts
    python -m app.alerts --force
"""

from __future__ import annotations

import argparse
import logging
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests

# Permitir ejecución directa (`python backend/app/alerts.py`) además de `python -m app.alerts`
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import get_env_settings, load_weights_config
from app.data_fetcher import DataRepository
from app.database import MacroDatabase
from app.indicators import compute_all_indicators
from app.scoring import build_dashboard_payload, compute_module_scores_and_composite

logger = logging.getLogger(__name__)


def evaluate_alert_trigger(
    payload: dict[str, Any],
    last_alert: dict[str, Any] | None,
    force: bool = False,
) -> tuple[bool, list[str]]:
    """Determina si corresponde emitir una alerta y explica los motivos exactos."""
    summary = payload["summary"]
    regime_key = summary["regime"]["key"]
    regime_label = summary["regime"]["label"]
    ew_active = bool(summary["early_warning_tech"]["active"])

    reasons: list[str] = []
    if force:
        reasons.append("Envío forzado (--force)")
        return True, reasons

    if last_alert is None:
        reasons.append(f"Estado inicial registrado ({regime_label})")
        if ew_active:
            reasons.append("Alerta Temprana Tech ACTIVA")
        return True, reasons

    prev_regime_key = last_alert.get("regime_key")
    prev_regime_label = last_alert.get("regime_label", prev_regime_key)
    prev_ew = bool(last_alert.get("tech_early_warning", 0))

    if regime_key != prev_regime_key:
        reasons.append(f"Cambio de régimen: {prev_regime_label} -> {regime_label}")

    if ew_active and not prev_ew:
        reasons.append("Activación de Alerta Temprana Tech (Riesgo de Techo Tech)")

    return len(reasons) > 0, reasons


def format_alert_message(
    payload: dict[str, Any],
    reasons: list[str],
    last_alert: dict[str, Any] | None = None,
) -> str:
    """Construye el cuerpo del mensaje para Telegram / Email con formato limpio."""
    summary = payload["summary"]
    regime = summary["regime"]
    ew = summary["early_warning_tech"]
    score = summary["growth_macro_score"]
    as_of = payload["as_of_date"]

    color_dot = {
        "red": "🔴",
        "amber": "🟠",
        "slate": "⚪",
        "teal": "🔵",
        "green": "🟢",
    }.get(regime.get("color", "slate"), "⚪")

    lines = [
        f"🧭 MacroCompass (Growth & Tech) · Cierre {as_of}",
        "",
        f"{color_dot} Growth Macro Score: {score:.1f} / 100 — {regime['label']}",
    ]

    if last_alert is not None:
        lines.append(
            f"Anterior: {float(last_alert['score']):.1f} ({last_alert['regime_label']})"
        )

    if reasons:
        lines.append("Motivo: " + " | ".join(reasons))

    if ew["active"]:
        lines.append("")
        lines.append(
            f"⚠️ ALERTA TEMPRANA TECH ACTIVA ({ew['conditions_met']}/{ew['required']} condiciones)"
        )
    else:
        lines.append(
            f"Alerta Temprana Tech: inactiva ({ew['conditions_met']}/{ew['required']} condiciones)"
        )

    for cond in ew["conditions"]:
        mark = "✅" if cond["met"] else "▫️"
        lines.append(f"  {mark} {cond['label']} [{cond['reading']}]")

    lines.extend(
        [
            "",
            "📋 Playbook:",
            regime["playbook"],
        ]
    )

    if summary.get("credit_priority_buy"):
        lines.append("")
        lines.append("🟢 ALERTA PRIORITARIA DE CRÉDITO: HY > 500 bp o BBB > 130 bp.")

    # Top módulos ordenados por contribución al extremo actual
    modules = [m for m in payload["modules"] if m.get("score") is not None]
    modules_sorted = sorted(modules, key=lambda m: float(m["score"]), reverse=(score >= 50))
    lines.append("")
    lines.append("📊 Desglose de módulos (0 compra — 100 euforia):")
    for m in modules_sorted:
        lines.append(
            f"  · M{m['number']} {m['title']}: {float(m['score']):.0f}/100 (peso {int(round(m['weight'] * 100))}%)"
        )

    return "\n".join(lines)


def send_telegram(message: str, bot_token: str, chat_id: str, timeout: int = 15) -> None:
    """Envía un mensaje de texto plano a Telegram mediante Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=timeout,
    )
    resp.raise_for_status()


def send_email_smtp(
    subject: str,
    body: str,
    host: str,
    port: int,
    user: str | None,
    password: str | None,
    mail_from: str,
    mail_to: str,
) -> None:
    """Envía el aviso por correo electrónico mediante SMTP con STARTTLS."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.ehlo()
        if port in (587, 25):
            try:
                server.starttls()
                server.ehlo()
            except smtplib.SMTPException:
                pass
        if user and password:
            server.login(user, password)
        server.send_message(msg)


def run_alert_check(
    dry_run: bool = False,
    force: bool = False,
    refresh_data: bool = True,
    db: MacroDatabase | None = None,
) -> dict[str, Any]:
    """Ejecuta el ciclo completo de evaluación, decisión y despacho de alertas."""
    env = get_env_settings()
    cfg = load_weights_config()
    database = db or MacroDatabase(env["db_path"])
    repo = DataRepository(db=database)

    df, metadata = repo.load_aligned_dataframe(refresh_if_stale=refresh_data, force_refresh=False)
    ind = compute_all_indicators(df, thresholds=cfg.get("thresholds"))
    scored = compute_module_scores_and_composite(ind, config=cfg)
    payload = build_dashboard_payload(scored, metadata=metadata, config=cfg)

    last_alert = database.get_last_alert()
    should_send, reasons = evaluate_alert_trigger(payload, last_alert=last_alert, force=force)
    message = format_alert_message(payload, reasons=reasons, last_alert=last_alert)

    summary = payload["summary"]
    sent_channels: list[str] = []
    errors: list[str] = []

    if should_send and not dry_run:
        if env["telegram_bot_token"] and env["telegram_chat_id"]:
            try:
                send_telegram(message, env["telegram_bot_token"], env["telegram_chat_id"])
                sent_channels.append("telegram")
            except Exception as exc:
                logger.error("Error enviando alerta a Telegram: %s", exc)
                errors.append(f"telegram: {exc}")

        if env["smtp_host"] and env["alert_email_to"]:
            mail_from = env["alert_email_from"] or env["smtp_user"] or "macrocompass@localhost"
            subject = (
                f"[MacroCompass] {summary['regime']['label']} "
                f"({summary['growth_macro_score']:.1f}/100)"
                + (" · ⚠️ Riesgo Techo Tech" if summary["early_warning_tech"]["active"] else "")
            )
            try:
                send_email_smtp(
                    subject=subject,
                    body=message,
                    host=env["smtp_host"],
                    port=env["smtp_port"],
                    user=env["smtp_user"],
                    password=env["smtp_pass"],
                    mail_from=mail_from,
                    mail_to=env["alert_email_to"],
                )
                sent_channels.append("email")
            except Exception as exc:
                logger.error("Error enviando alerta por SMTP: %s", exc)
                errors.append(f"email: {exc}")

        if not sent_channels and not errors:
            sent_channels.append("local_log_only")

        database.record_alert(
            as_of_date=payload["as_of_date"],
            score=summary["growth_macro_score"],
            regime_key=summary["regime"]["key"],
            regime_label=summary["regime"]["label"],
            tech_early_warning=bool(summary["early_warning_tech"]["active"]),
            tech_conditions_met=int(summary["early_warning_tech"]["conditions_met"]),
            channels=sent_channels,
            message=message,
            dry_run=False,
        )

    return {
        "as_of_date": payload["as_of_date"],
        "score": summary["growth_macro_score"],
        "regime": summary["regime"]["label"],
        "tech_early_warning": summary["early_warning_tech"]["active"],
        "should_send": should_send,
        "reasons": reasons,
        "dry_run": dry_run,
        "channels_sent": sent_channels,
        "errors": errors,
        "message": message,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MacroCompass — Evaluador diario de alertas macro (Telegram + SMTP)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evalúa los datos y muestra la alerta generada sin enviar ni modificar el historial.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fuerza el disparo aunque no haya cambiado el régimen.",
    )
    parser.add_argument(
        "--no-refresh",
        action="store_true",
        help="Usa únicamente la caché local SQLite sin descargar datos nuevos.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    result = run_alert_check(
        dry_run=args.dry_run,
        force=args.force,
        refresh_data=not args.no_refresh,
    )

    print("=" * 72)
    print(
        f"MacroCompass Alerts | Fecha: {result['as_of_date']} | "
        f"Dry-Run: {result['dry_run']} | Disparar: {result['should_send']}"
    )
    if result["reasons"]:
        print("Motivos:", " | ".join(result["reasons"]))
    else:
        print("Motivos: Sin cambio de régimen ni nueva activación de Alerta Temprana Tech.")
    print("-" * 72)
    print(result["message"])
    print("=" * 72)

    if result["errors"]:
        print("Errores de envío:", result["errors"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
