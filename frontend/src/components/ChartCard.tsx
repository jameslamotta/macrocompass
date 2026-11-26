"use client";

import type { ReactNode } from "react";
import { scoreColorClasses } from "./ModuleScoreStrip";

interface ChartCardProps {
  id: string;
  number: number;
  title: string;
  subtitle: string;
  weight: number;
  score: number | null;
  interpretation: string;
  badge?: ReactNode;
  kpis?: ReactNode;
  children: ReactNode;
}

export function ChartCard({
  id,
  number,
  title,
  subtitle,
  weight,
  score,
  interpretation,
  badge,
  kpis,
  children,
}: ChartCardProps) {
  return (
    <section
      id={`module-${id}`}
      className="scroll-mt-20 border-t border-[#E6E8EC] pt-7 pb-3"
    >
      {/* Cabecera editorial fiel a las capturas: título en negrita + subtítulo gris en línea + score */}
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1.5">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 className="text-[19px] font-bold tracking-[-0.02em] text-[#111827]">
            {title}
          </h2>
          <span className="text-[12.5px] font-normal text-[#7B8494]">
            {subtitle}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {badge}
          <span className="text-[11px] font-medium text-[#7B8494] tabular-nums">
            M{number} · Peso {Math.round(weight * 100)}%
          </span>
          <span
            className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-bold tabular-nums ${scoreColorClasses(
              score
            )}`}
            title="Puntuación normalizada del módulo (0 = Capitulación, 100 = Euforia)"
          >
            {score !== null ? `${score.toFixed(0)}/100` : "N/D"}
          </span>
        </div>
      </div>

      {/* Fila opcional de KPIs grandes en negrita */}
      {kpis && <div className="mt-3.5">{kpis}</div>}

      {/* Área de gráfico */}
      <div className="mt-4">{children}</div>

      {/* Nota interpretativa directa al pie (estilo de las capturas) */}
      <p className="mt-3 text-[13px] leading-snug font-semibold text-[#1F2937]">
        {interpretation}
      </p>
    </section>
  );
}
