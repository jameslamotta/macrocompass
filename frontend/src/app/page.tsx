"use client";

import { useCallback, useEffect, useState } from "react";
import { BacktestPanel } from "@/components/BacktestPanel";
import { HeaderBar } from "@/components/HeaderBar";
import { ModuleScoreStrip } from "@/components/ModuleScoreStrip";
import { PlaybookBanner } from "@/components/PlaybookBanner";
import { CyclicalsDefensivesModule } from "@/components/modules/CyclicalsDefensivesModule";
import { LiquidityModule } from "@/components/modules/LiquidityModule";
import { MarketBreadthModule } from "@/components/modules/MarketBreadthModule";
import { PriceOfRiskModule } from "@/components/modules/PriceOfRiskModule";
import { RealRatesModule } from "@/components/modules/RealRatesModule";
import { TechExtensionModule } from "@/components/modules/TechExtensionModule";
import { VolatilityModule } from "@/components/modules/VolatilityModule";
import { fetchBacktest, fetchDashboard, triggerRefresh } from "@/lib/api";
import type {
  AnyModuleData,
  BacktestPayload,
  DashboardPayload,
} from "@/lib/types";

function renderModule(mod: AnyModuleData) {
  switch (mod.id) {
    case "liquidity":
      return <LiquidityModule key={mod.id} data={mod} />;
    case "real_rates":
      return <RealRatesModule key={mod.id} data={mod} />;
    case "tech_extension":
      return <TechExtensionModule key={mod.id} data={mod} />;
    case "market_breadth":
      return <MarketBreadthModule key={mod.id} data={mod} />;
    case "volatility":
      return <VolatilityModule key={mod.id} data={mod} />;
    case "price_of_risk":
      return <PriceOfRiskModule key={mod.id} data={mod} />;
    case "cyclicals_defensives":
      return <CyclicalsDefensivesModule key={mod.id} data={mod} />;
  }
}

export default function MacroCompassPage() {
  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
  const [backtest, setBacktest] = useState<BacktestPayload | null>(null);
  const [ticker, setTicker] = useState<"QQQ" | "SMH" | "SPY">("QQQ");
  const [loading, setLoading] = useState(true);
  const [btLoading, setBtLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async (selectedTicker: "QQQ" | "SMH" | "SPY") => {
    try {
      const [dashData, btData] = await Promise.all([
        fetchDashboard(),
        fetchBacktest(selectedTicker, 10),
      ]);
      setError(null);
      setDashboard(dashData);
      setBacktest(btData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando datos macro.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [dashData, btData] = await Promise.all([
          fetchDashboard(),
          fetchBacktest("QQQ", 10),
        ]);
        if (!active) return;
        setError(null);
        setDashboard(dashData);
        setBacktest(btData);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Error cargando datos macro.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const handleSelectTicker = async (nextTicker: "QQQ" | "SMH" | "SPY") => {
    setTicker(nextTicker);
    setBtLoading(true);
    try {
      const btData = await fetchBacktest(nextTicker, 10);
      setBacktest(btData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando backtest.");
    } finally {
      setBtLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      await triggerRefresh();
      await loadAll(ticker);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error actualizando datos.");
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white px-6 text-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#E5E7EB] border-t-[#2573C2]" />
        <p className="mt-4 text-sm font-medium text-[#111827]">
          Cargando MacroCompass (Edición Growth &amp; Tech)...
        </p>
        <p className="mt-1 text-xs text-[#6B7280]">
          Sincronizando series de FRED, Yahoo Finance y motor de scoring causal
        </p>
      </div>
    );
  }

  if (error && !dashboard) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white px-6 text-center">
        <div className="max-w-md rounded-2xl border border-[#FECACA] bg-[#FEF2F2] p-6">
          <h2 className="text-base font-bold text-[#991B1B]">
            No se pudo conectar con el motor de datos
          </h2>
          <p className="mt-2 text-xs leading-relaxed text-[#7F1D1D]">{error}</p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              loadAll(ticker);
            }}
            className="mt-4 cursor-pointer rounded-lg bg-[#111827] px-4 py-2 text-xs font-semibold text-white hover:bg-[#1F2937]"
          >
            Reintentar conexión
          </button>
        </div>
      </div>
    );
  }

  if (!dashboard) return null;

  return (
    <div className="min-h-screen bg-white text-[#111827]">
      <HeaderBar
        asOfDate={dashboard.as_of_date}
        metadata={dashboard.metadata}
        refreshing={refreshing}
        onRefresh={handleRefresh}
      />

      <main className="mx-auto max-w-[1260px] space-y-6 px-4 py-6 sm:px-6 lg:px-8">
        {error && (
          <div className="rounded-xl border border-[#FDE68A] bg-[#FFFBEB] px-4 py-2.5 text-xs font-medium text-[#92400E]">
            Aviso: {error}
          </div>
        )}

        <PlaybookBanner summary={dashboard.summary} />

        <ModuleScoreStrip modules={dashboard.modules} />

        {/* Los 7 módulos calibrados a Growth & Tech */}
        <div className="space-y-4">
          {dashboard.modules.map((mod) => renderModule(mod))}
        </div>

        {/* Backtest Histórico 10 años */}
        <BacktestPanel
          data={backtest}
          ticker={ticker}
          loading={btLoading}
          onSelectTicker={handleSelectTicker}
        />

        <footer className="border-t border-[#E6E8EC] pt-5 pb-8 text-[11.5px] text-[#7B8494]">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span>
              MacroCompass · Edición Growth &amp; Tech · Pesos configurables en{" "}
              <code className="rounded bg-[#F3F4F6] px-1 py-0.5 font-mono text-[11px] text-[#374151]">
                config/weights.yaml
              </code>
            </span>
            <span>
              Datos: FRED (St. Louis Fed) y Yahoo Finance · Herramienta analítica, no constituye asesoramiento financiero.
            </span>
          </div>
        </footer>
      </main>
    </div>
  );
}
