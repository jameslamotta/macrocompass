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
import type { LiquidityModuleData } from "@/lib/types";

export function LiquidityModule({ data }: { data: LiquidityModuleData }) {
  const { kpis, series } = data;
  const yearTicks = getYearTicks(series, 1);
  const isContracting =
    kpis.net_liq_roc_3m_pct !== null && kpis.net_liq_roc_3m_pct < 0;

  return (
    <ChartCard
      id={data.id}
      number={data.number}
      title={data.title}
      subtitle={data.subtitle}
      weight={data.weight}
      score={data.score}
      interpretation={data.interpretation}
      kpis={
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-2 rounded-xl bg-[#F5F6F8] px-4 py-3">
          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              Liquidez Neta Fed
            </div>
            <div className="text-[26px] leading-tight font-bold tracking-tight text-[#111827] tabular-nums">
              {kpis.net_liquidity_bn !== null
                ? `$${kpis.net_liquidity_bn.toLocaleString("es-ES")}B`
                : "N/D"}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              Cambio 3 meses
            </div>
            <div
              className={`text-[22px] leading-tight font-bold tabular-nums ${
                isContracting ? "text-[#B91C1C]" : "text-[#15803D]"
              }`}
            >
              {formatSigned(kpis.net_liq_roc_3m_pct, "%", 1)}
              <span className="ml-2 text-xs font-medium text-[#6B7280]">
                ({formatSigned(kpis.net_liq_chg_3m_bn, "B", 0)})
              </span>
            </div>
          </div>

          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              Chicago Fed NFCI
            </div>
            <div className="text-[22px] leading-tight font-bold text-[#111827] tabular-nums">
              {formatSigned(kpis.nfci, "", 2)}
            </div>
          </div>

          <div className="ml-auto hidden text-right text-[11px] text-[#6B7280] tabular-nums sm:block">
            <div>WALCL: ${kpis.walcl_bn?.toLocaleString("es-ES") ?? "—"}B</div>
            <div>
              TGA: ${kpis.tga_bn?.toLocaleString("es-ES") ?? "—"}B · RRP: $
              {kpis.rrp_bn?.toLocaleString("es-ES") ?? "—"}B
            </div>
          </div>
        </div>
      }
    >
      <div className="space-y-3">
        {/* Panel superior: Liquidez Neta ($B) */}
        <div>
          <div className="mb-1 flex items-center justify-between text-[11.5px] text-[#6B7280]">
            <span>
              Liquidez Neta de la Fed (miles de millones USD) · 5 años
            </span>
            <span className="tabular-nums">
              3M: {formatSigned(kpis.net_liq_roc_3m_pct, "%", 1)}
            </span>
          </div>
          <div className="h-[195px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={series}
                syncId="liquidity-sync"
                margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
              >
                <CartesianGrid stroke="#EFEFEF" vertical={false} />
                <XAxis
                  dataKey="date"
                  ticks={yearTicks}
                  tickFormatter={formatYearTick}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={["auto", "auto"]}
                  width={52}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  tickFormatter={(v) => `$${(Number(v) / 1000).toFixed(1)}T`}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  labelFormatter={(l) => formatDateES(String(l))}
                  formatter={(value, name) => {
                    const num = Number(value);
                    if (name === "net_liquidity_bn") {
                      return [`$${num.toLocaleString("es-ES", { maximumFractionDigits: 0 })}B`, "Liquidez Neta"];
                    }
                    return [`${num.toFixed(1)}%`, "RoC 3M"];
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="net_liquidity_bn"
                  stroke="#2573C2"
                  strokeWidth={1.7}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Panel inferior: RoC 3M (%) y NFCI */}
        <div>
          <div className="mb-1 flex items-center justify-between text-[11.5px] text-[#6B7280]">
            <span>
              Tasa de cambio Liquidez 3M (%) y Condiciones Financieras (NFCI · eje der.)
            </span>
            <span className="flex items-center gap-3 text-[11px]">
              <span className="inline-flex items-center gap-1">
                <span className="h-0.5 w-3 bg-[#2573C2]" /> Liquidez 3M (%)
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="h-0.5 w-3 bg-[#D97706]" /> NFCI
              </span>
            </span>
          </div>
          <div className="h-[155px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={series}
                syncId="liquidity-sync"
                margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
              >
                <CartesianGrid stroke="#EFEFEF" vertical={false} />
                <ReferenceArea
                  yAxisId="left"
                  y1={-15}
                  y2={0}
                  fill="#DC2626"
                  fillOpacity={0.055}
                />
                <ReferenceLine
                  yAxisId="left"
                  y={0}
                  stroke="#9CA3AF"
                  strokeDasharray="3 3"
                />
                <XAxis
                  dataKey="date"
                  ticks={yearTicks}
                  tickFormatter={formatYearTick}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  yAxisId="left"
                  width={52}
                  domain={[-12, 12]}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  tickFormatter={(v) => `${v}%`}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  width={42}
                  domain={[-1, 1.2]}
                  tick={{ fill: "#B45309", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  labelFormatter={(l) => formatDateES(String(l))}
                  formatter={(value, name) => {
                    const num = Number(value);
                    if (name === "roc_3m_pct") return [`${num >= 0 ? "+" : ""}${num.toFixed(1)}%`, "Liquidez 3M"];
                    return [num.toFixed(2), "NFCI"];
                  }}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="roc_3m_pct"
                  stroke="#2573C2"
                  strokeWidth={1.6}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="nfci"
                  stroke="#D97706"
                  strokeWidth={1.4}
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
