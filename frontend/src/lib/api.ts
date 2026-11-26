import type { BacktestPayload, DashboardPayload } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export async function fetchDashboard(): Promise<DashboardPayload> {
  const res = await fetch(`${API_BASE}/api/dashboard`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Error ${res.status} cargando dashboard: ${text}`);
  }
  return res.json();
}

export async function fetchBacktest(
  ticker: "QQQ" | "SMH" | "SPY",
  years: number = 10
): Promise<BacktestPayload> {
  const res = await fetch(
    `${API_BASE}/api/backtest?ticker=${encodeURIComponent(ticker)}&years=${years}`,
    { cache: "no-store" }
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Error ${res.status} cargando backtest ${ticker}: ${text}`);
  }
  return res.json();
}

export async function triggerRefresh(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/refresh`, {
    method: "POST",
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Error ${res.status} refrescando datos: ${text}`);
  }
}

export function formatSigned(
  value: number | null | undefined,
  suffix = "",
  digits = 1
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/D";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}${suffix}`;
}

export function formatDateES(isoDate: string): string {
  if (!isoDate) return "";
  const [y, m, d] = isoDate.split("-");
  if (!y || !m || !d) return isoDate;
  return `${d}/${m}/${y}`;
}

export function formatYearTick(isoDate: string): string {
  return isoDate ? isoDate.slice(0, 4) : "";
}

export function getYearTicks(
  series: Array<{ date: string }>,
  stepYears: number = 1
): string[] {
  const seen = new Set<number>();
  const ticks: string[] = [];
  for (const pt of series) {
    if (!pt.date || pt.date.length < 4) continue;
    const year = Number(pt.date.slice(0, 4));
    if (Number.isNaN(year) || seen.has(year)) continue;
    seen.add(year);
    if (stepYears <= 1 || year % stepYears === 0) {
      ticks.push(pt.date);
    }
  }
  return ticks;
}

