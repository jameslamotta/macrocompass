"use client";

import { useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatDateES, formatSigned, formatYearTick, getYearTicks } from "@/lib/api";
import type { BacktestPayload } from "@/lib/types";

interface BacktestPanelProps {
  data: BacktestPayload | null;
  ticker: "QQQ" | "SMH" | "SPY";
  loading: boolean;
  onSelectTicker: (ticker: "QQQ" | "SMH" | "SPY") => void;
}

const TICKERS: Array<{ id: "QQQ" | "SMH" | "SPY"; label: string }> = [
  { id: "QQQ", label: "QQQ · Nasdaq 100" },
  { id: "SMH", label: "SMH · Semiconductores" },
  { id: "SPY", label: "SPY · S&P 500" },
];

function SignalDot({
  cx,
  cy,
  fill,
  r = 3.3,
  payload,
  field,
}: {
  cx?: number;
  cy?: number;
  fill: string;
  r?: number;
  payload?: Record<string, unknown>;
  field: "red_marker" | "green_marker";
}) {
  const val = payload ? payload[field] : null;
  if (
    val === null ||
    val === undefined ||
    cx === undefined ||
    cy === undefined ||
    Number.isNaN(cx) ||
    Number.isNaN(cy)
  ) {
    return null;
  }
  return (
    <circle
      cx={cx}
      cy={cy}
      r={r}
      fill={fill}
      stroke="#FFFFFF"
      strokeWidth={0.9}
    />
  );
}

function fmtEpisodes(n: number): string {
  return n === 1 ? "1 episodio" : `${n} episodios`;
}

export function BacktestPanel({
  data,
  ticker,
  loading,
  onSelectTicker,
}: BacktestPanelProps) {
  const [logScale, setLogScale] = useState(true);
  const yearTicks = data ? getYearTicks(data.series, 1) : [];

  return (
    <section
      id="backtest-section"
      className="scroll-mt-20 border-t-2 border-[#111827] pt-7 pb-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h2 className="text-[20px] font-bold tracking-[-0.02em] text-[#111827]">
              Backtest Histórico (10 años) · Señales Macro vs. {ticker}
            </h2>
            <span className="text-[12.5px] text-[#7B8494]">
              cálculo estrictamente causal (sin look-ahead bias) · puntos rojos = Score ≥ 80 o Alerta Temprana Tech · puntos verdes = Score &lt; 20
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div
            className="inline-flex rounded-lg border border-[#E5E7EB] bg-[#F5F6F8] p-0.5"
            role="group"
            aria-label="Selector de activo para backtest"
          >
            {TICKERS.map((item) => (
              <button
                key={item.id}
                id={`btn-backtest-${item.id.toLowerCase()}`}
                type="button"
                onClick={() => onSelectTicker(item.id)}
                className={`cursor-pointer rounded-md px-3 py-1 text-xs font-semibold transition ${
                  ticker === item.id
                    ? "bg-white text-[#111827] shadow-xs"
                    : "text-[#6B7280] hover:text-[#111827]"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          <button
            id="btn-backtest-scale"
            type="button"
            onClick={() => setLogScale((v) => !v)}
            className="cursor-pointer rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1.5 text-xs font-medium text-[#374151] transition hover:bg-[#F9FAFB]"
          >
            Escala: {logScale ? "Log" : "Lineal"}
          </button>
        </div>
      </div>

      {/* Tarjetas de estadísticas descriptivas de señales */}
      {data && (
        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <div className="rounded-xl bg-[#ECFDF5]/70 px-4 py-3">
            <div className="text-[11px] font-semibold text-[#15803D]">
              🟢 Zona Capitulación (&lt; 20)
            </div>
            <div className="mt-1 text-xl font-bold text-[#111827] tabular-nums">
              {fmtEpisodes(data.stats.green_zone.episodes)}
              <span className="ml-1.5 text-xs font-normal text-[#6B7280]">
                ({data.stats.green_zone.days} ses.)
              </span>
            </div>
            <div className="mt-1 text-[11.5px] text-[#374151] tabular-nums">
              Retorno medio +3M:{" "}
              <strong>{formatSigned(data.stats.green_zone.avg_fwd_3m_pct, "%")}</strong>{" "}
              · +6M:{" "}
              <strong>{formatSigned(data.stats.green_zone.avg_fwd_6m_pct, "%")}</strong>
            </div>
          </div>

          <div className="rounded-xl bg-[#FEF2F2]/80 px-4 py-3">
            <div className="text-[11px] font-semibold text-[#B91C1C]">
              🔴 Euforia (&gt; 80) o Alerta Tech
            </div>
            <div className="mt-1 text-xl font-bold text-[#111827] tabular-nums">
              {fmtEpisodes(data.stats.red_zone.episodes)}
              <span className="ml-1.5 text-xs font-normal text-[#6B7280]">
                ({data.stats.red_zone.days} ses.)
              </span>
            </div>
            <div className="mt-1 text-[11.5px] text-[#374151] tabular-nums">
              Retorno medio +3M:{" "}
              <strong>{formatSigned(data.stats.red_zone.avg_fwd_3m_pct, "%")}</strong>{" "}
              · +6M:{" "}
              <strong>{formatSigned(data.stats.red_zone.avg_fwd_6m_pct, "%")}</strong>
            </div>
          </div>

          <div className="rounded-xl bg-[#FFFBEB]/80 px-4 py-3">
            <div className="text-[11px] font-semibold text-[#B45309]">
              ⚠️ Solo Alerta Temprana Tech
            </div>
            <div className="mt-1 text-xl font-bold text-[#111827] tabular-nums">
              {fmtEpisodes(data.stats.tech_early_warning.episodes)}
              <span className="ml-1.5 text-xs font-normal text-[#6B7280]">
                ({data.stats.tech_early_warning.days} ses.)
              </span>
            </div>
            <div className="mt-1 text-[11.5px] text-[#374151] tabular-nums">
              Retorno medio +3M:{" "}
              <strong>
                {formatSigned(data.stats.tech_early_warning.avg_fwd_3m_pct, "%")}
              </strong>{" "}
              · +6M:{" "}
              <strong>
                {formatSigned(data.stats.tech_early_warning.avg_fwd_6m_pct, "%")}
              </strong>
            </div>
          </div>

          <div className="rounded-xl bg-[#F4F5F7] px-4 py-3">
            <div className="text-[11px] font-semibold text-[#4B5563]">
              Base Histórica ({ticker} · 10 años)
            </div>
            <div className="mt-1 text-xl font-bold text-[#111827] tabular-nums">
              {data.start_date.slice(0, 4)}–{data.end_date.slice(0, 4)}
            </div>
            <div className="mt-1 text-[11.5px] text-[#374151] tabular-nums">
              Media +3M:{" "}
              <strong>{formatSigned(data.stats.baseline.avg_fwd_3m_pct, "%")}</strong>{" "}
              · +6M:{" "}
              <strong>{formatSigned(data.stats.baseline.avg_fwd_6m_pct, "%")}</strong>
            </div>
          </div>
        </div>
      )}

      {/* Gráficos sincronizados: Precio con puntos de señal + Score 0-100 */}
      {loading || !data ? (
        <div className="mt-5 flex h-[430px] items-center justify-center rounded-xl bg-[#F8F9FA] text-sm text-[#6B7280]">
          Cargando serie histórica de {ticker}...
        </div>
      ) : (
        <div className="mt-5 space-y-3">
          <div>
            <div className="mb-1 flex items-center justify-between text-[12px] text-[#6B7280]">
              <span>
                Precio ajustado de <strong className="text-[#111827]">{ticker}</strong> (USD) con marcadores de régimen extremo
              </span>
              <span className="flex items-center gap-3 text-[11px]">
                <span className="inline-flex items-center gap-1 text-[#B91C1C]">
                  <span className="h-2 w-2 rounded-full bg-[#DC2626]" /> Score ≥ 80 / Alerta Tech
                </span>
                <span className="inline-flex items-center gap-1 text-[#15803D]">
                  <span className="h-2 w-2 rounded-full bg-[#16A34A]" /> Score &lt; 20
                </span>
              </span>
            </div>

            <div className="h-[265px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={data.series}
                  syncId="backtest-sync"
                  margin={{ top: 10, right: 18, left: 4, bottom: 0 }}
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
                    width={52}
                    scale={logScale ? "log" : "linear"}
                    domain={["auto", "auto"]}
                    tick={{ fill: "#8B929E", fontSize: 11 }}
                    tickFormatter={(v) => `$${Number(v).toFixed(0)}`}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    labelFormatter={(l) => formatDateES(String(l))}
                    formatter={(value, name) => {
                      if (value === null || value === undefined) return [null, ""];
                      if (name === "price") return [`$${Number(value).toFixed(2)}`, ticker];
                      if (name === "red_marker") return [`$${Number(value).toFixed(2)}`, "Señal Roja (Euforia / Tech)"];
                      if (name === "green_marker") return [`$${Number(value).toFixed(2)}`, "Señal Verde (Capitulación)"];
                      return [String(value), String(name)];
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="price"
                    stroke="#1F2937"
                    strokeWidth={1.6}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Scatter
                    dataKey="red_marker"
                    fill="#DC2626"
                    shape={<SignalDot fill="#DC2626" r={3.2} field="red_marker" />}
                    isAnimationActive={false}
                  />
                  <Scatter
                    dataKey="green_marker"
                    fill="#16A34A"
                    shape={<SignalDot fill="#16A34A" r={4.4} field="green_marker" />}
                    isAnimationActive={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between text-[12px] text-[#6B7280]">
              <span>Growth Macro Score compuesto (0–100) · mismo eje temporal</span>
              <span className="text-[11px]">
                <span className="text-[#B91C1C]">banda roja &gt; 80</span> ·{" "}
                <span className="text-[#15803D]">banda verde &lt; 20</span>
              </span>
            </div>
            <div className="h-[195px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={data.series}
                  syncId="backtest-sync"
                  margin={{ top: 8, right: 18, left: 4, bottom: 0 }}
                >
                  <CartesianGrid stroke="#EFEFEF" vertical={false} />
                  <ReferenceArea y1={80} y2={100} fill="#DC2626" fillOpacity={0.085} />
                  <ReferenceArea y1={0} y2={20} fill="#16A34A" fillOpacity={0.095} />
                  <XAxis
                    dataKey="date"
                    ticks={yearTicks}
                    tickFormatter={formatYearTick}
                    tick={{ fill: "#8B929E", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    width={52}
                    domain={[0, 100]}
                    ticks={[0, 20, 50, 80, 100]}
                    tick={{ fill: "#8B929E", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    labelFormatter={(l) => formatDateES(String(l))}
                    formatter={(value) => [`${Number(value).toFixed(1)} / 100`, "Growth Macro Score"]}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#2573C2"
                    strokeWidth={1.65}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
