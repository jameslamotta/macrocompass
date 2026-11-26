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
import { formatDateES, formatYearTick, getYearTicks } from "@/lib/api";
import type { VolatilityModuleData } from "@/lib/types";

export function VolatilityModule({ data }: { data: VolatilityModuleData }) {
  const { kpis, series } = data;
  const yearTicks = getYearTicks(series, 1);
  const isComplacent =
    (kpis.vxn ?? 99) < 17 && (kpis.vix_term_ratio ?? 9) < 0.85;
  const isCapitulation =
    (kpis.vxn ?? 0) > 32 && (kpis.vix_term_ratio ?? 0) > 1.0;

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
        isComplacent ? (
          <span className="rounded-full border border-[#FECACA] bg-[#FEF2F2] px-2.5 py-0.5 text-[11px] font-semibold text-[#B91C1C]">
            Complacencia / Cobertura barata
          </span>
        ) : isCapitulation ? (
          <span className="rounded-full border border-[#BBF7D0] bg-[#ECFDF5] px-2.5 py-0.5 text-[11px] font-semibold text-[#15803D]">
            Capitulación / Backwardation
          </span>
        ) : undefined
      }
      kpis={
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-2 rounded-xl bg-[#F5F6F8] px-4 py-3">
          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              Volatilidad Nasdaq-100 (^VXN)
            </div>
            <div
              className={`text-[26px] leading-tight font-bold tabular-nums ${
                (kpis.vxn ?? 20) < 17
                  ? "text-[#B91C1C]"
                  : (kpis.vxn ?? 20) > 32
                  ? "text-[#15803D]"
                  : "text-[#111827]"
              }`}
            >
              {kpis.vxn !== null ? kpis.vxn.toFixed(1) : "N/D"}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              Estructura Temporal (^VIX / ^VIX3M)
            </div>
            <div
              className={`text-[26px] leading-tight font-bold tabular-nums ${
                (kpis.vix_term_ratio ?? 0.9) < 0.85
                  ? "text-[#B91C1C]"
                  : (kpis.vix_term_ratio ?? 0.9) > 1.0
                  ? "text-[#15803D]"
                  : "text-[#111827]"
              }`}
            >
              {kpis.vix_term_ratio !== null
                ? kpis.vix_term_ratio.toFixed(2)
                : "N/D"}
              <span className="ml-2 text-xs font-medium text-[#6B7280]">
                {(kpis.vix_term_ratio ?? 0.9) > 1.0
                  ? "backwardation"
                  : "contango"}
              </span>
            </div>
          </div>

          <div className="ml-auto hidden text-right text-[11px] text-[#6B7280] tabular-nums sm:block">
            <div>
              ^VIX: {kpis.vix?.toFixed(1) ?? "—"} · ^VIX3M:{" "}
              {kpis.vix3m?.toFixed(1) ?? "—"}
            </div>
            <div>
              Euforia: ^VXN &lt; 17 y ratio &lt; 0.85 · Capitulación: ^VXN &gt; 32 y ratio &gt; 1.0
            </div>
          </div>
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Izquierda: ^VXN */}
        <div>
          <div className="mb-1 flex items-center justify-between text-[11.5px] text-[#6B7280]">
            <span>^VXN (Volatilidad implícita Nasdaq-100) · 5 años</span>
            <span className="text-[11px]">
              <span className="text-[#15803D]">verde &gt; 32</span> ·{" "}
              <span className="text-[#B91C1C]">rojo &lt; 17</span>
            </span>
          </div>
          <div className="h-[210px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={series}
                syncId="vol-sync"
                margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
              >
                <CartesianGrid stroke="#EFEFEF" vertical={false} />
                <ReferenceArea y1={32} y2={65} fill="#16A34A" fillOpacity={0.09} />
                <ReferenceArea y1={10} y2={17} fill="#DC2626" fillOpacity={0.08} />
                <ReferenceLine y={32} stroke="#16A34A" strokeOpacity={0.4} strokeDasharray="3 3" />
                <ReferenceLine y={17} stroke="#DC2626" strokeOpacity={0.4} strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  ticks={yearTicks}
                  tickFormatter={formatYearTick}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  width={38}
                  domain={[10, 55]}
                  ticks={[10, 17, 25, 32, 45, 55]}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  labelFormatter={(l) => formatDateES(String(l))}
                  formatter={(value) => [Number(value).toFixed(1), "^VXN"]}
                />
                <Line
                  type="monotone"
                  dataKey="vxn"
                  stroke="#2573C2"
                  strokeWidth={1.65}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Derecha: ^VIX / ^VIX3M */}
        <div>
          <div className="mb-1 flex items-center justify-between text-[11.5px] text-[#6B7280]">
            <span>Ratio ^VIX / ^VIX3M (estructura temporal) · 5 años</span>
            <span className="text-[11px]">
              <span className="text-[#15803D]">&gt; 1.0 backwardation</span> ·{" "}
              <span className="text-[#B91C1C]">&lt; 0.85 complacencia</span>
            </span>
          </div>
          <div className="h-[210px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={series}
                syncId="vol-sync"
                margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
              >
                <CartesianGrid stroke="#EFEFEF" vertical={false} />
                <ReferenceArea y1={1.0} y2={1.4} fill="#16A34A" fillOpacity={0.09} />
                <ReferenceArea y1={0.7} y2={0.85} fill="#DC2626" fillOpacity={0.08} />
                <ReferenceLine y={1.0} stroke="#16A34A" strokeOpacity={0.45} strokeDasharray="3 3" />
                <ReferenceLine y={0.85} stroke="#DC2626" strokeOpacity={0.4} strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  ticks={yearTicks}
                  tickFormatter={formatYearTick}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  width={42}
                  domain={[0.72, 1.3]}
                  ticks={[0.75, 0.85, 1.0, 1.15, 1.3]}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  tickFormatter={(v) => Number(v).toFixed(2)}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  labelFormatter={(l) => formatDateES(String(l))}
                  formatter={(value) => [Number(value).toFixed(2), "^VIX / ^VIX3M"]}
                />
                <Line
                  type="monotone"
                  dataKey="vix_term_ratio"
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
