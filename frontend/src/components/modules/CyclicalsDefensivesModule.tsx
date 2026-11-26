"use client";

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
import { formatDateES, formatYearTick, getYearTicks } from "@/lib/api";
import type { CyclicalsModuleData } from "@/lib/types";

export function CyclicalsDefensivesModule({
  data,
}: {
  data: CyclicalsModuleData;
}) {
  const { kpis, series } = data;
  const yearTicks = getYearTicks(series, 2);
  const lastPoint = series[series.length - 1];
  const xlkPct = kpis.xlk_xlp_2y_pct;

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
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tabular-nums ${
            (xlkPct ?? 50) >= 80
              ? "border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C]"
              : (xlkPct ?? 50) <= 20
              ? "border-[#BBF7D0] bg-[#ECFDF5] text-[#15803D]"
              : "border-[#E5E7EB] bg-[#F5F6F8] text-[#374151]"
          }`}
        >
          XLK / XLP (Tech vs Consumo Básico) · Percentil 2A:{" "}
          <strong>{xlkPct !== null ? `${xlkPct.toFixed(0)}%` : "N/D"}</strong>
        </span>
      }
    >
      {/* Gráfico editorial fiel a la captura "Cyclicals Against Defensives" */}
      <div className="relative h-[265px] w-full">
        <span className="pointer-events-none absolute top-2.5 left-11 z-10 text-[10.5px] font-medium text-[#B91C1C]/80">
          rojo = estirado, recortar cíclicos hacia defensivos
        </span>
        <span className="pointer-events-none absolute right-14 bottom-8 z-10 text-[10.5px] font-medium text-[#15803D]/85">
          verde = lavado, comprar cíclicos
        </span>

        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={series}
            margin={{ top: 8, right: 44, left: 0, bottom: 0 }}
          >
            <CartesianGrid stroke="#EFEFEF" vertical={false} />
            <ReferenceArea y1={80} y2={100} fill="#DC2626" fillOpacity={0.08} />
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
              width={34}
              domain={[0, 100]}
              ticks={[0, 20, 50, 80, 100]}
              tick={{ fill: "#8B929E", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              labelFormatter={(l) => formatDateES(String(l))}
              formatter={(value, name) => {
                if (name === "ma5") return [`${Number(value).toFixed(0)} / 100`, "Cíclicos / Defensivos (MA5)"];
                return [`${Number(value).toFixed(0)}%`, "XLK / XLP (P2A)"];
              }}
            />
            <Line
              type="monotone"
              dataKey="ma5"
              stroke="#2573C2"
              strokeWidth={1.6}
              dot={false}
              isAnimationActive={false}
            />
            {lastPoint && lastPoint.ma5 !== null && (
              <ReferenceDot
                x={lastPoint.date}
                y={lastPoint.ma5}
                r={4.2}
                fill="#111827"
                stroke="#FFFFFF"
                strokeWidth={1.5}
                label={{
                  value: `${lastPoint.ma5.toFixed(0)}`,
                  position: "right",
                  fill: "#111827",
                  fontSize: 12.5,
                  fontWeight: 700,
                }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}
