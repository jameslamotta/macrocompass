"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "@/components/ChartCard";
import { formatDateES, formatSigned, formatYearTick, getYearTicks } from "@/lib/api";
import type { TechExtensionModuleData } from "@/lib/types";

export function TechExtensionModule({ data }: { data: TechExtensionModuleData }) {
  const { kpis, series } = data;
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
      kpis={
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-2 rounded-xl bg-[#F5F6F8] px-4 py-3">
          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              QQQ vs SMA 200
            </div>
            <div
              className={`text-[26px] leading-tight font-bold tabular-nums ${
                (kpis.qqq_dist_sma200_pct ?? 0) > 16
                  ? "text-[#B91C1C]"
                  : (kpis.qqq_dist_sma200_pct ?? 0) < -10
                  ? "text-[#15803D]"
                  : "text-[#111827]"
              }`}
            >
              {formatSigned(kpis.qqq_dist_sma200_pct, "%", 1)}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              SMH (Semis) vs SMA 200
            </div>
            <div
              className={`text-[26px] leading-tight font-bold tabular-nums ${
                (kpis.smh_dist_sma200_pct ?? 0) > 25
                  ? "text-[#B91C1C]"
                  : (kpis.smh_dist_sma200_pct ?? 0) < -15
                  ? "text-[#15803D]"
                  : "text-[#111827]"
              }`}
            >
              {formatSigned(kpis.smh_dist_sma200_pct, "%", 1)}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-medium text-[#6B7280]">
              IWF / IWD (Growth vs Value · 2A)
            </div>
            <div
              className={`text-[26px] leading-tight font-bold tabular-nums ${
                (kpis.iwf_iwd_2y_minmax ?? 50) > 85
                  ? "text-[#B91C1C]"
                  : (kpis.iwf_iwd_2y_minmax ?? 50) < 20
                  ? "text-[#15803D]"
                  : "text-[#111827]"
              }`}
            >
              {kpis.iwf_iwd_2y_minmax !== null
                ? `${kpis.iwf_iwd_2y_minmax.toFixed(0)} / 100`
                : "N/D"}
            </div>
          </div>

          <div className="ml-auto hidden text-right text-[11px] text-[#6B7280] sm:block">
            <div>Euforia: QQQ &gt; +16% · SMH &gt; +25% · Growth &gt; 85</div>
            <div>Capitulación: QQQ &lt; -10% · SMH &lt; -15%</div>
          </div>
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Izquierda: QQQ y SMH % sobre SMA 200 */}
        <div>
          <div className="mb-1 flex items-center justify-between text-[11.5px] text-[#6B7280]">
            <span>Distancia porcentual respecto a SMA 200 (%)</span>
            <span className="flex items-center gap-3 text-[11px]">
              <span className="inline-flex items-center gap-1">
                <span className="h-0.5 w-3 bg-[#2573C2]" /> QQQ
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="h-0.5 w-3 bg-[#0F766E]" /> SMH
              </span>
            </span>
          </div>
          <div className="h-[220px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={series}
                syncId="tech-ext-sync"
                margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
              >
                <CartesianGrid stroke="#EFEFEF" vertical={false} />
                <ReferenceArea y1={16} y2={60} fill="#DC2626" fillOpacity={0.075} />
                <ReferenceArea y1={-40} y2={-10} fill="#16A34A" fillOpacity={0.08} />
                <ReferenceLine y={16} stroke="#DC2626" strokeOpacity={0.35} strokeDasharray="3 3" />
                <ReferenceLine y={0} stroke="#CBD5E1" />
                <ReferenceLine y={-10} stroke="#16A34A" strokeOpacity={0.4} strokeDasharray="3 3" />
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
                  domain={[-35, 45]}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  tickFormatter={(v) => `${v}%`}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  labelFormatter={(l) => formatDateES(String(l))}
                  formatter={(value, name) => {
                    const num = Number(value);
                    return [
                      `${num >= 0 ? "+" : ""}${num.toFixed(1)}%`,
                      name === "qqq_dist" ? "QQQ vs SMA200" : "SMH vs SMA200",
                    ];
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="qqq_dist"
                  stroke="#2573C2"
                  strokeWidth={1.7}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="smh_dist"
                  stroke="#0F766E"
                  strokeWidth={1.45}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Derecha: IWF/IWD 0-100 con bandas roja >80 y verde <20 */}
        <div>
          <div className="mb-1 flex items-center justify-between text-[11.5px] text-[#6B7280]">
            <span>Ratio Growth / Value (IWF / IWD) · rango móvil 2 años (0–100)</span>
            <span className="text-[11px] text-[#B91C1C]">euforia &gt; 85</span>
          </div>
          <div className="relative h-[220px] w-full">
            <span className="pointer-events-none absolute top-2.5 left-12 z-10 text-[10px] font-medium text-[#B91C1C]/80">
              rojo = growth estirado (&gt;80)
            </span>
            <span className="pointer-events-none absolute right-10 bottom-8 z-10 text-[10px] font-medium text-[#15803D]/85">
              verde = lavado (&lt;20)
            </span>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={series}
                syncId="tech-ext-sync"
                margin={{ top: 8, right: 38, left: 0, bottom: 0 }}
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
                  ticks={[0, 20, 50, 80, 100]}
                  tick={{ fill: "#8B929E", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  labelFormatter={(l) => formatDateES(String(l))}
                  formatter={(value) => [`${Number(value).toFixed(0)} / 100`, "IWF/IWD (2A)"]}
                />
                <Line
                  type="monotone"
                  dataKey="iwf_iwd_0_100"
                  stroke="#2573C2"
                  strokeWidth={1.65}
                  dot={false}
                  isAnimationActive={false}
                />
                {lastPoint && lastPoint.iwf_iwd_0_100 !== null && (
                  <ReferenceDot
                    x={lastPoint.date}
                    y={lastPoint.iwf_iwd_0_100}
                    r={4}
                    fill="#111827"
                    stroke="#FFFFFF"
                    strokeWidth={1.5}
                    label={{
                      value: `${lastPoint.iwf_iwd_0_100.toFixed(0)}`,
                      position: "right",
                      fill: "#111827",
                      fontSize: 12,
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
