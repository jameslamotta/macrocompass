"use client";

import type { AnyModuleData } from "@/lib/types";

interface ModuleScoreStripProps {
  modules: AnyModuleData[];
}

const SHORT_NAMES: Record<string, string> = {
  liquidity: "Liquidez & NFCI",
  real_rates: "Tipos Reales",
  tech_extension: "Tech & Semis",
  market_breadth: "Amplitud",
  volatility: "Volatilidad VXN",
  price_of_risk: "Crédito OAS",
  cyclicals_defensives: "Cíclicos / Def.",
};

export function scoreColorClasses(score: number | null): string {
  if (score === null) return "bg-[#F3F4F6] text-[#6B7280]";
  if (score >= 80) return "bg-[#FEF2F2] text-[#B91C1C]";
  if (score >= 65) return "bg-[#FFFBEB] text-[#B45309]";
  if (score < 20) return "bg-[#ECFDF5] text-[#15803D]";
  if (score < 35) return "bg-[#F0FDFA] text-[#0F766E]";
  return "bg-[#F3F4F6] text-[#374151]";
}

export function ModuleScoreStrip({ modules }: ModuleScoreStripProps) {
  return (
    <nav
      aria-label="Resumen rápido de los 7 módulos"
      className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8"
    >
      {modules.map((m) => (
        <a
          key={m.id}
          href={`#module-${m.id}`}
          className="group flex flex-col justify-between rounded-xl border border-[#EAECF0] bg-white px-3 py-2.5 transition hover:border-[#CBD5E1] hover:bg-[#FAFBFD]"
        >
          <div className="flex items-center justify-between text-[11px] text-[#7B8494]">
            <span>M{m.number}</span>
            <span className="tabular-nums">{Math.round(m.weight * 100)}%</span>
          </div>
          <div className="mt-1 truncate text-xs font-semibold text-[#111827] group-hover:text-[#2573C2]">
            {SHORT_NAMES[m.id] || m.title}
          </div>
          <div className="mt-2 flex items-center justify-between">
            <span
              className={`rounded-md px-1.5 py-0.5 text-xs font-bold tabular-nums ${scoreColorClasses(
                m.score
              )}`}
            >
              {m.score !== null ? m.score.toFixed(0) : "N/D"}
            </span>
            <span className="text-[10px] text-[#9CA3AF]">/100</span>
          </div>
        </a>
      ))}

      <a
        href="#backtest-section"
        className="group flex flex-col justify-between rounded-xl border border-[#DBEAFE] bg-[#F8FAFF] px-3 py-2.5 transition hover:border-[#93C5FD]"
      >
        <div className="flex items-center justify-between text-[11px] text-[#2573C2]">
          <span>Histórico</span>
          <span>10A</span>
        </div>
        <div className="mt-1 truncate text-xs font-semibold text-[#1E3A8A]">
          Backtest QQQ
        </div>
        <div className="mt-2 text-[11px] font-medium text-[#2573C2]">
          Ver señales →
        </div>
      </a>
    </nav>
  );
}
