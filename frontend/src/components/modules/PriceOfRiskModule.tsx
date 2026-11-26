"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "@/components/ChartCard";
import { formatDateES, formatSigned } from "@/lib/api";
import type { CreditSpreadCard, PriceOfRiskModuleData } from "@/lib/types";

function SpreadMiniCard({
  card,
  windowLabel,
}: {
  card: CreditSpreadCard;
  windowLabel: string;
}) {
  const statusLevel = card.status.level;
  const dotColor =
    statusLevel === "buy"
      ? "bg-[#DC2626]"
      : statusLevel === "watch"
      ? "bg-[#D97706]"
      : statusLevel === "tight"
      ? "bg-[#2573C2]"
      : "bg-[#16A34A]";

  const statusTextColor =
    statusLevel === "buy"
      ? "text-[#B91C1C]"
      : statusLevel === "watch"
      ? "text-[#B45309]"
      : statusLevel === "tight"
      ? "text-[#1D4ED8]"
      : "text-[#15803D]";

  return (
    <div className="rounded-xl bg-[#F4F5F7] p-5">
      {/* Cabecera de tarjeta con punto de estado (estilo The Price of Risk) */}
      <div className="flex items-center gap-2">
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${dotColor}`} />
        <h3 className="text-[13.5px] font-bold text-[#111827]">{card.label}</h3>
      </div>

      {/* KPI principal en negrita grande + deltas y percentil en línea */}
      <div className="mt-2.5 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-[30px] leading-none font-extrabold tracking-tight text-[#111827] tabular-nums">
          {card.value_bp !== null ? `${card.value_bp.toFixed(0)} bp` : "N/D"}
        </span>
        <span className="text-[11.5px] text-[#6B7280] tabular-nums">
          {formatSigned(card.chg_1m_bp, " bp", 0)} en 1M ·{" "}
          {formatSigned(card.chg_3m_bp, " bp", 0)} en 3M · percentil{" "}
          {card.percentile !== null ? `${card.percentile.toFixed(0)}%` : "N/D"} (
          {windowLabel})
        </span>
      </div>

      {/* Etiqueta de estado directa */}
      <div className={`mt-1.5 text-[12.5px] font-bold ${statusTextColor}`}>
        {card.status.text}
      </div>

      {/* Micro-leyenda + Sparkline 5 años con línea gris de mediana histórica */}
      <div className="mt-3 flex items-center justify-between text-[10.5px] text-[#8B929E]">
        <span>
          sparkline · línea gris = mediana ({card.median_bp?.toFixed(0) ?? "—"} bp)
        </span>
        <span className="text-[#15803D]">
          compra prioritaria &gt; {card.buy_threshold_bp.toFixed(0)} bp
        </span>
      </div>

      <div className="mt-1 h-[105px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={card.series}
            margin={{ top: 6, right: 8, left: 0, bottom: 2 }}
          >
            <CartesianGrid stroke="#E7E9EE" vertical={false} />
            <XAxis dataKey="date" hide />
            <YAxis
              width={36}
              domain={["auto", "auto"]}
              tick={{ fill: "#8B929E", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickCount={3}
            />
            {card.median_bp !== null && (
              <ReferenceLine y={card.median_bp} stroke="#9CA3AF" strokeWidth={1.1} />
            )}
            <ReferenceLine
              y={card.buy_threshold_bp}
              stroke="#16A34A"
              strokeDasharray="3 3"
              strokeOpacity={0.55}
            />
            <Tooltip
              labelFormatter={(l) => formatDateES(String(l))}
              formatter={(value) => [`${Number(value).toFixed(0)} bp`, "OAS"]}
            />
            <Line
              type="monotone"
              dataKey="value_bp"
              stroke="#2573C2"
              strokeWidth={1.6}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function PriceOfRiskModule({ data }: { data: PriceOfRiskModuleData }) {
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
        data.priority_buy_alert ? (
          <span className="rounded-full border border-[#BBF7D0] bg-[#ECFDF5] px-2.5 py-0.5 text-[11px] font-bold text-[#15803D]">
            🟢 Alerta Prioritaria de Compra
          </span>
        ) : data.is_limited_csv_window ? (
          <span
            className="rounded-full bg-[#F3F4F6] px-2.5 py-0.5 text-[11px] font-medium text-[#6B7280]"
            title="Añade FRED_API_KEY en .env para ampliar el historial de crédito ICE BofA a 10+ años"
          >
            Ventana CSV: 3 años (añade FRED_API_KEY para 10A)
          </span>
        ) : undefined
      }
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <SpreadMiniCard card={data.hy} windowLabel={data.window_label} />
        <SpreadMiniCard card={data.bbb} windowLabel={data.window_label} />
      </div>
    </ChartCard>
  );
}
