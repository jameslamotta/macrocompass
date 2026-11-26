"""Pruebas del motor de alertas (cambio de régimen, Alerta Tech, deduplicación y --dry-run)."""

from __future__ import annotations

from app.alerts import evaluate_alert_trigger, format_alert_message
from app.database import MacroDatabase


def _sample_payload(score: float, regime_key: str, regime_label: str, ew_active: bool) -> dict:
    return {
        "as_of_date": "2026-11-25",
        "summary": {
            "growth_macro_score": score,
            "regime": {
                "key": regime_key,
                "label": regime_label,
                "color": "red" if score >= 80 else "slate",
                "playbook": "Playbook de prueba.",
            },
            "early_warning_tech": {
                "active": ew_active,
                "conditions_met": 3 if ew_active else 1,
                "required": 3,
                "conditions": [
                    {"id": "extension", "label": "QQQ/SMH", "met": ew_active, "reading": "QQQ +16%"},
                    {"id": "vxn", "label": "^VXN", "met": ew_active, "reading": "^VXN 16.0"},
                    {"id": "liq_rates", "label": "Liq/DFII10", "met": ew_active, "reading": "Liq -1%"},
                    {"id": "breadth_growth", "label": "Amplitud", "met": False, "reading": "Div No"},
                ],
            },
            "credit_priority_buy": False,
        },
        "modules": [
            {"number": 1, "title": "Liquidez Neta", "score": score, "weight": 0.20},
        ],
    }


def test_alert_triggers_only_on_regime_change_or_new_tech_warning():
    # 1) Primera ejecución (sin estado previo) -> dispara
    p_neutral = _sample_payload(52.0, "neutral", "Neutral", ew_active=False)
    should, reasons = evaluate_alert_trigger(p_neutral, last_alert=None)
    assert should is True
    assert any("inicial" in r.lower() for r in reasons)

    prev_neutral = {
        "score": 52.0,
        "regime_key": "neutral",
        "regime_label": "Neutral",
        "tech_early_warning": 0,
    }

    # 2) Mismo régimen sin nueva alerta tech -> silencio
    should, reasons = evaluate_alert_trigger(p_neutral, last_alert=prev_neutral)
    assert should is False
    assert reasons == []

    # 3) Cambio de régimen (Neutral -> Euforia extrema) -> dispara
    p_euphoria = _sample_payload(84.0, "euforia_extrema", "Euforia extrema", ew_active=False)
    should, reasons = evaluate_alert_trigger(p_euphoria, last_alert=prev_neutral)
    assert should is True
    assert any("Cambio de régimen" in r for r in reasons)

    # 4) Mismo régimen pero Alerta Temprana Tech pasa de inactiva a activa -> dispara
    p_neutral_ew = _sample_payload(58.0, "neutral", "Neutral", ew_active=True)
    should, reasons = evaluate_alert_trigger(p_neutral_ew, last_alert=prev_neutral)
    assert should is True
    assert any("Alerta Temprana Tech" in r for r in reasons)

    # 5) Si al día siguiente sigue igual (Neutral + Tech EW ya activa) -> silencio (sin spam)
    prev_ew = {
        "score": 58.0,
        "regime_key": "neutral",
        "regime_label": "Neutral",
        "tech_early_warning": 1,
    }
    should, _ = evaluate_alert_trigger(p_neutral_ew, last_alert=prev_ew)
    assert should is False


def test_format_alert_message_and_sqlite_state(tmp_path):
    db = MacroDatabase(tmp_path / "test_alerts.db")
    assert db.get_last_alert() is None

    payload = _sample_payload(83.5, "euforia_extrema", "Euforia extrema", ew_active=True)
    msg = format_alert_message(payload, reasons=["Cambio de régimen"])
    assert "MacroCompass" in msg
    assert "83.5 / 100" in msg
    assert "ALERTA TEMPRANA TECH ACTIVA" in msg

    db.record_alert(
        as_of_date="2026-11-25",
        score=83.5,
        regime_key="euforia_extrema",
        regime_label="Euforia extrema",
        tech_early_warning=True,
        tech_conditions_met=3,
        channels=["local_log_only"],
        message=msg,
        dry_run=False,
    )
    last = db.get_last_alert()
    assert last is not None
    assert last["regime_key"] == "euforia_extrema"
    assert last["tech_early_warning"] == 1
