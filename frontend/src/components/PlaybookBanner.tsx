"use client";

import { AlertTriangle, CheckCircle2, Circle, ShieldAlert } from "lucide-react";
import { formatSigned } from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";

interface PlaybookBannerProps {
  summary: DashboardSummary;
}

const REGIME_STYLES: Record<
  string,
  { badge: string; accent: string; scoreColor: string; barBg: string }
> = {
  red: {
    badge: "bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]",
    accent: "bg-[#DC2626]",
    scoreColor: "text-[#B91C1C]",
    barBg: "bg-[#FEF2F2]/60 border-[#FECACA]",
  },
  amber: {
    badge: "bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]",
    accent: "bg-[#D97706]",
    scoreColor: "text-[#B45309]",
    barBg: "bg-[#FFFBEB]/60 border-[#FDE68A]",
  },
  slate: {
    badge: "bg-[#F3F4F6] text-[#374151] border-[#E5E7EB]",
    accent: "bg-[#4B5563]",
    scoreColor: "text-[#111827]",
    barBg: "bg-[#F8F9FA] border-[#E5E7EB]",
  },
  teal: {
    badge: "bg-[#F0FDFA] text-[#0F766E] border-[#99F6E4]",
    accent: "bg-[#0D9488]",
    scoreColor: "text-[#0F766E]",
    barBg: "bg-[#F0FDFA]/60 border-[#99F6E4]",
  },
  green: {
    badge: "bg-[#ECFDF5] text-[#15803D] border-[#BBF7D0]",
    accent: "bg-[#16A34A]",
    scoreColor: "text-[#15803D]",
    barBg: "bg-[#ECFDF5]/70 border-[#BBF7D0]",
  },
};

export function PlaybookBanner({ summary }: PlaybookBannerProps) {
  const { growth_macro_score, score_1w_delta, score_1m_delta, regime, early_warning_tech, credit_priority_buy } =
    summary;
  const style = REGIME_STYLES[regime.color] || REGIME_STYLES.slate;
  const clampedPct = Math.max(0, Math.min(100, growth_macro_score));

  return (
    <section
      id="playbook-banner"
      aria-label="Growth Macro Score y Playbook táctico"
      className="rounded-2xl border border-[#E6E8EC] bg-[#FAFBFD] p-5 sm:p-6"
    >
      {/* Fila superior: Score compuesto + Playbook directo */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-center">
        {/* Columna izquierda: Score 0-100 y barra de temperatura */}
        <div className="lg:col-span-5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-semibold tracking-[0.08em] text-[#6B7280] uppercase">
              Growth Macro Score
            </span>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${style.badge}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${style.accent}`} />
              {regime.label}
            </span>
          </div>

          <div className="mt-2 flex items-baseline gap-3">
            <span
              id="macro-score-value"
              className={`text-[46px] leading-none font-extrabold tracking-[-0.04em] tabular-nums ${style.scoreColor}`}
            >
              {growth_macro_score.toFixed(1)}
            </span>
            <span className="text-lg font-medium text-[#9CA3AF] tabular-nums">
              / 100
            </span>
            <div className="ml-auto flex items-center gap-3 text-xs text-[#6B7280] tabular-nums">
              <span>1S: {formatSigned(score_1w_delta, "", 1)}</span>
              <span>1M: {formatSigned(score_1m_delta, "", 1)}</span>
            </div>
          </div>

          {/* Barra horizontal de zonas 0..100 */}
          <div className="mt-4">
            <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-[#ECEFF3]">
              <div className="absolute inset-y-0 left-0 w-[20%] bg-[#16A34A]/25" />
              <div className="absolute inset-y-0 left-[20%] w-[15%] bg-[#0D9488]/15" />
              <div className="absolute inset-y-0 left-[35%] w-[30%] bg-[#9CA3AF]/15" />
              <div className="absolute inset-y-0 left-[65%] w-[15%] bg-[#D97706]/20" />
              <div className="absolute inset-y-0 left-[80%] w-[20%] bg-[#DC2626]/25" />
              {/* Marcador actual */}
              <div
                className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-[#111827] shadow-sm transition-all"
                style={{ left: `${clampedPct}%` }}
                aria-hidden="true"
              />
            </div>
            <div className="mt-1.5 flex justify-between text-[10px] font-medium text-[#7B8494] tabular-nums">
              <span className="text-[#15803D]">0 Capitulación</span>
              <span>20</span>
              <span>35</span>
              <span>65</span>
              <span>80</span>
              <span className="text-[#B91C1C]">100 Euforia</span>
            </div>
          </div>
        </div>

        {/* Columna derecha: Playbook táctico accionable */}
        <div className="lg:col-span-7">
          <div className={`rounded-xl border p-4 sm:p-5 ${style.barBg}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[11px] font-semibold tracking-[0.08em] text-[#4B5563] uppercase">
                Playbook táctico activo
              </span>
              <div className="flex flex-wrap items-center gap-2">
                {regime.sahm_caution && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-[#FEF2F2] px-2.5 py-0.5 text-[11px] font-semibold text-[#B91C1C]">
                    <ShieldAlert className="h-3.5 w-3.5" />
                    Sahm ≥ 0.50: espaciar tramos varias semanas
                  </span>
                )}
                {credit_priority_buy && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-[#ECFDF5] px-2.5 py-0.5 text-[11px] font-semibold text-[#15803D]">
                    Oportunidad de Crédito (HY &gt; 500 bp / BBB &gt; 130 bp)
                  </span>
                )}
              </div>
            </div>
            <p
              id="playbook-text"
              className="mt-2 text-[15px] leading-relaxed font-semibold text-[#111827]"
            >
              {regime.playbook}
            </p>
          </div>
        </div>
      </div>

      {/* Franja inferior: Override táctico — Alerta Temprana Tech (3 de 4) */}
      <div
        id="early-warning-panel"
        className={`mt-5 rounded-xl border p-4 transition-colors ${
          early_warning_tech.active
            ? "border-[#FCA5A5] bg-[#FEF2F2]"
            : "border-[#E6E8EC] bg-white"
        }`}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {early_warning_tech.active ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-[#DC2626] px-3 py-1 text-xs font-bold text-white">
                <AlertTriangle className="h-3.5 w-3.5" />
                ⚠️ {early_warning_tech.badge_label}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-[#F3F4F6] px-2.5 py-0.5 text-xs font-semibold text-[#374151]">
                Alerta Temprana Tech (Override táctico)
              </span>
            )}
            <span
              className={`text-xs font-medium tabular-nums ${
                early_warning_tech.active ? "text-[#991B1B]" : "text-[#6B7280]"
              }`}
            >
              {early_warning_tech.conditions_met} de 4 condiciones activas (dispara con ≥{" "}
              {early_warning_tech.required})
            </span>
          </div>

          <span className="text-[11px] text-[#6B7280]">
            Independiente del score global · Protección contra techos tech abruptos
          </span>
        </div>

        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {early_warning_tech.conditions.map((cond) => (
            <div
              key={cond.id}
              className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-xs ${
                cond.met
                  ? "border-[#FECACA] bg-[#FEF2F2]/70 text-[#7F1D1D]"
                  : "border-[#EDF0F3] bg-[#FAFBFD] text-[#4B5563]"
              }`}
            >
              {cond.met ? (
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#DC2626]" />
              ) : (
                <Circle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#CBD5E1]" />
              )}
              <div className="min-w-0">
                <div className="font-semibold leading-snug">{cond.label}</div>
                <div className="mt-0.5 text-[11px] opacity-85 tabular-nums">
                  {cond.reading}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
