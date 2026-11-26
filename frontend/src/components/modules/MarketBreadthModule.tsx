"use client";

import { AlertTriangle } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "@/components/ChartCard";
import { formatDateES, formatSigned, formatYearTick, getYearTicks } from "@/lib/api";
import type { MarketBreadthModuleData } from "@/lib/types";

export function MarketBreadthModule({ data }: { data: MarketBreadthModuleData }) {
  const { kpis, series, bearish_divergence } = data;
  const yearTicks = getYearTicks(series, 1);
  const lastPoint = series[series.length - 1];

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
        bearish_divergence ? (
          <span className="inline-flex items-center gap-1 rounded-full border border-[#FECACA] bg-[#FEF2F2] px-2.5 py-0.5 text-[11px] font-semibold text-[#B91C1C]">
            <AlertTriangle className="h-3 w-3" />
            Divergencia bajista QQQE/QQQ
          </span>
        ) : undefined
      }
    >
      <div className="space-y-4">
        {/* Gráfico superior (5 años): RSP/SPY + SMA 200 y línea secundaria QQQE/QQQ (base 100) */}
        <div>
          <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-[12px] text-[#6B7280]">
            <span>
              La acción media frente al índice, 5 años (inicio = 100) · cayendo = pocos grandes nombres sostienen el mercado · RSP/SPY 3M{" "}
              <strong className="font-semibold text-[#111827] tabular-nums">
                {formatSigned(kpis.rsp_spy_roc_3m_pct, "%", 1)}
              </strong>{" "}
              · QQQE/QQQ 3M{" "}
              <strong className="font-semibold text-[#111827] tabular-nums">
                {formatSigned(kpis.qqqe_qqq_roc_3m_pct, "%", 1)}
              </strong>
            </span>
            <span className="flex items-center gap-3 text-[11px]">
              <span className="inline-flex items-center gap-1">
                <span className="h-0.5 w-3 bg-[#2573C2]" /> RSP / SPY
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="h-0.5 w-3 bg-[#B4BCC8]" /> SMA 200
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="h-0.5 w-3 bg-[#0F766E]" /> QQQE / QQQ
              </span>
            </span>
          </div>

          <div className="h-[225px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={series}
                syncId="breadth-sync"
                margin={{ top: 8, right: 46, left: 0, bottom: 0 }}
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
                  width={38}
                  domain={["auto", "auto"]}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  labelFormatter={(l) => formatDateES(String(l))}
                  formatter={(value, name) => {
                    const labels: Record<string, string> = {
                      rsp_spy: "RSP / SPY (base 100)",
                      rsp_spy_sma200: "RSP / SPY SMA 200",
                      qqqe_qqq: "QQQE / QQQ (base 100)",
                      qqqe_qqq_sma200: "QQQE / QQQ SMA 200",
                    };
                    return [Number(value).toFixed(1), labels[String(name)] || String(name)];
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="rsp_spy_sma200"
                  stroke="#B8C0CC"
                  strokeWidth={1.3}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="qqqe_qqq_sma200"
                  stroke="#99F6E4"
                  strokeWidth={1.1}
                  strokeDasharray="3 3"
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="rsp_spy"
                  stroke="#2573C2"
                  strokeWidth={1.65}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="qqqe_qqq"
                  stroke="#0F766E"
                  strokeWidth={1.45}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Gráfico inferior (5 años, mismo eje): % de los 11 ETFs sectoriales > SMA 200 */}
        <div>
          <div className="mb-1 flex items-center justify-between text-[12px] text-[#6B7280]">
            <span>
              Porcentaje de los 11 ETFs sectoriales sobre su media de 200 sesiones, 5 años (%) · banda verde = lavado, primer tramo de compra · hoy{" "}
              <strong className="font-semibold text-[#111827] tabular-nums">
                {kpis.pct_sectors_above_sma200 !== null
                  ? `${kpis.pct_sectors_above_sma200.toFixed(0)}%`
                  : "N/D"}
              </strong>{" "}
              ({kpis.sectors_above}/{kpis.sectors_total})
            </span>
          </div>

          <div className="relative h-[220px] w-full">
            <span className="pointer-events-none absolute top-2.5 left-12 z-10 text-[10px] font-medium text-[#B91C1C]/80">
              rojo &gt; 80% = sobrecompra amplia
            </span>
            <span className="pointer-events-none absolute right-14 bottom-8 z-10 text-[10px] font-medium text-[#15803D]/85">
              verde &lt; 20% = lavado, comprar primer tramo
            </span>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={series}
                syncId="breadth-sync"
                margin={{ top: 8, right: 46, left: 0, bottom: 0 }}
              >
                <CartesianGrid stroke="#EFEFEF" vertical={false} />
                <ReferenceArea y1={80} y2={100} fill="#DC2626" fillOpacity={0.08} />
                <ReferenceArea y1={0} y2={20} fill="#16A34A" fillOpacity={0.09} />
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
                  domain={[0, 100]}
                  ticks={[0, 20, 40, 60, 80, 100]}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  labelFormatter={(l) => formatDateES(String(l))}
                  formatter={(value) => [
                    `${Number(value).toFixed(0)}%`,
                    "Sectores > SMA 200",
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="pct_sectors"
                  stroke="#2573C2"
                  strokeWidth={1.6}
                  dot={false}
                  isAnimationActive={false}
                />
                {lastPoint && lastPoint.pct_sectors !== null && (
                  <ReferenceDot
                    x={lastPoint.date}
                    y={lastPoint.pct_sectors}
                    r={4}
                    fill="#111827"
                    stroke="#FFFFFF"
                    strokeWidth={1.5}
                    label={{
                      value: `${lastPoint.pct_sectors.toFixed(0)}%`,
                      position: "right",
                      fill: "#111827",
                      fontSize: 11.5,
                      fontWeight: 700,
                    }}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </ChartCard>
  );
}
