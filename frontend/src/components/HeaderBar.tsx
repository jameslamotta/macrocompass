"use client";

import { Compass, RefreshCw } from "lucide-react";
import { formatDateES } from "@/lib/api";
import type { DashboardMetadata } from "@/lib/types";

interface HeaderBarProps {
  asOfDate: string;
  metadata: DashboardMetadata;
  refreshing: boolean;
  onRefresh: () => void;
}

export function HeaderBar({
  asOfDate,
  metadata,
  refreshing,
  onRefresh,
}: HeaderBarProps) {
  const isApiMode = metadata.fred_source_mode === "fred_api";

  return (
    <header className="sticky top-0 z-30 border-b border-[#E6E8EC] bg-white/95 backdrop-blur-sm">
      <div className="mx-auto flex max-w-[1260px] flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#111827] text-white">
            <Compass className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <h1 className="text-[19px] font-bold tracking-[-0.025em] text-[#111827]">
                MacroCompass
              </h1>
              <span className="text-xs font-medium tracking-wide text-[#2573C2]">
                Edición Growth &amp; Tech
              </span>
            </div>
            <p className="text-[12px] text-[#6B7280]">
              Brújula macro para carteras Tech, Semis y Growth · 0 = Capitulación · 100 = Euforia
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-medium ${
              isApiMode
                ? "bg-[#ECFDF5] text-[#15803D]"
                : "bg-[#F3F4F6] text-[#4B5563]"
            }`}
            title={
              isApiMode
                ? "Conectado con FRED_API_KEY (historial completo)"
                : "Modo sin clave: CSV público de FRED (añade FRED_API_KEY para historial 10Y en crédito)"
            }
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isApiMode ? "bg-[#16A34A]" : "bg-[#2573C2]"
              }`}
            />
            {isApiMode ? "FRED API" : "FRED CSV público"}
          </span>

          <span className="rounded-full bg-[#F5F6F8] px-2.5 py-1 font-medium text-[#374151] tabular-nums">
            Cierre: {formatDateES(asOfDate)}
          </span>

          <button
            id="btn-refresh-data"
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-[#D1D5DB] bg-white px-3 py-1.5 font-medium text-[#111827] transition hover:bg-[#F9FAFB] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
            />
            {refreshing ? "Actualizando..." : "Actualizar"}
          </button>
        </div>
      </div>
    </header>
  );
}
