"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "@/components/ChartCard";
import { formatDateES, formatSigned, formatYearTick, getYearTicks } from "@/lib/api";
import type { RealRatesModuleData } from "@/lib/types";

export function RealRatesModule({ data }: { data: RealRatesModuleData }) {
  const { kpis, series, cycle_label } = data;
  const yearTicks = getYearTicks(series, 1);

  const cycleBadgeClass =
    cycle_label === "Alerta Recesión"
      ? "bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]"
      : cycle_label === "Presión de Tipos"
      ? "bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]"
      : "bg-[#ECFDF5] text-[#15803D] border-[#BBF7D0]";

  const shock3mHot = (kpis.dfii10_chg_3m_bp ?? 0) >= 35;
  const shock1mHot = (kpis.dfii10_chg_1m_bp ?? 0) >= 35;

  return (
    <ChartCard
      id={data.id}
      number={data.number}
      title={data.title}
      subtitle={data.subtitle}
      weight={data.weight}
      score={data.score}
      interpretation={data.interpretation}
      badge={
        <span
          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${cycleBadgeClass}`}
        >
          Ciclo: {cycle_label}
        </span>
      }
      kpis={
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-2 rounded-xl bg-[#F5F6F8] px-4 py-3">
          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              Tipo Real 10A (DFII10)
            </div>
            <div className="text-[26px] leading-tight font-bold text-[#111827] tabular-nums">
              {kpis.dfii10 !== null ? `${kpis.dfii10.toFixed(2)}%` : "N/D"}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              Variación 1M / 3M
            </div>
            <div className="flex items-baseline gap-2.5 text-[20px] leading-tight font-bold tabular-nums">
              <span className={shock1mHot ? "text-[#B91C1C]" : "text-[#111827]"}>
                {formatSigned(kpis.dfii10_chg_1m_bp, " pb", 0)}
                <span className="ml-1 text-[11px] font-normal text-[#6B7280]">
                  1M
                </span>
              </span>
              <span className="text-[#CBD5E1]">·</span>
              <span className={shock3mHot ? "text-[#B91C1C]" : "text-[#111827]"}>
                {formatSigned(kpis.dfii10_chg_3m_bp, " pb", 0)}
                <span className="ml-1 text-[11px] font-normal text-[#6B7280]">
                  3M
                </span>
              </span>
            </div>
          </div>

          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              Curva 10Y-2Y (T10Y2Y)
            </div>
            <div
              className={`text-[20px] leading-tight font-bold tabular-nums ${
                (kpis.t10y2y ?? 0) < 0 ? "text-[#B45309]" : "text-[#111827]"
              }`}
            >
              {formatSigned(kpis.t10y2y, "%", 2)}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              Regla de Sahm
            </div>
            <div
              className={`text-[20px] leading-tight font-bold tabular-nums ${
                (kpis.sahm ?? 0) >= 0.5 ? "text-[#B91C1C]" : "text-[#15803D]"
              }`}
            >
              {kpis.sahm !== null ? kpis.sahm.toFixed(2) : "N/D"}
              <span className="ml-1 text-[11px] font-normal text-[#6B7280]">
                (alerta ≥ 0.50)
              </span>
            </div>
          </div>
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Izquierda: Nivel DFII10 y T10Y2Y */}
        <div>
          <div className="mb-1 flex items-center justify-between text-[11.5px] text-[#6B7280]">
            <span>Tipo Real 10A (DFII10, %) y Pendiente 10Y-2Y (%)</span>
            <span className="flex items-center gap-3 text-[11px]">
              <span className="inline-flex items-center gap-1">
                <span className="h-0.5 w-3 bg-[#2573C2]" /> DFII10
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="h-0.5 w-3 bg-[#9CA3AF]" /> T10Y2Y
              </span>
            </span>
          </div>
          <div className="h-[210px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={series}
                syncId="rates-sync"
                margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
              >
                <CartesianGrid stroke="#EFEFEF" vertical={false} />
                <ReferenceLine y={0} stroke="#CBD5E1" strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  ticks={yearTicks}
                  tickFormatter={formatYearTick}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  width={44}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  tickFormatter={(v) => `${Number(v).toFixed(1)}%`}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  labelFormatter={(l) => formatDateES(String(l))}
                  formatter={(value, name) => [
                    `${Number(value).toFixed(2)}%`,
                    name === "dfii10" ? "DFII10 (Real 10A)" : "Curva 10Y-2Y",
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="dfii10"
                  stroke="#2573C2"
                  strokeWidth={1.7}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="t10y2y"
                  stroke="#9CA3AF"
                  strokeWidth={1.3}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Derecha: Choque 3M en pb de DFII10 */}
        <div>
          <div className="mb-1 flex items-center justify-between text-[11.5px] text-[#6B7280]">
            <span>Velocidad de tipos reales: Δ 3M de DFII10 (pb)</span>
            <span className="text-[11px] text-[#B91C1C]">
              zona roja: &gt; +35 pb (presión growth)
            </span>
          </div>
          <div className="h-[210px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={series}
                syncId="rates-sync"
                margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
              >
                <CartesianGrid stroke="#EFEFEF" vertical={false} />
                <ReferenceArea y1={35} y2={150} fill="#DC2626" fillOpacity={0.08} />
                <ReferenceArea y1={-150} y2={-35} fill="#16A34A" fillOpacity={0.08} />
                <ReferenceLine y={35} stroke="#DC2626" strokeOpacity={0.35} strokeDasharray="3 3" />
                <ReferenceLine y={0} stroke="#CBD5E1" />
                <XAxis
                  dataKey="date"
                  ticks={yearTicks}
                  tickFormatter={formatYearTick}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  width={48}
                  domain={[-110, 120]}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  tickFormatter={(v) => `${v} bp`}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  labelFormatter={(l) => formatDateES(String(l))}
                  formatter={(value) => {
                    const num = Number(value);
                    return [`${num >= 0 ? "+" : ""}${num.toFixed(0)} pb`, "Δ 3M DFII10"];
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="chg_3m_bp"
                  stroke="#1E3A5F"
                  strokeWidth={1.6}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </ChartCard>
  );
}
