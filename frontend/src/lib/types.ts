export interface RegimeInfo {
  key: string;
  label: string;
  color: "red" | "amber" | "slate" | "teal" | "green" | string;
  playbook: string;
  sahm_caution: boolean;
}

export interface EarlyWarningCondition {
  id: string;
  label: string;
  met: boolean;
  reading: string;
}

export interface EarlyWarningTech {
  active: boolean;
  conditions_met: number;
  required: number;
  badge_label: string;
  conditions: EarlyWarningCondition[];
}

export interface CreditHistoryMeta {
  hy_min_date: string | null;
  bbb_min_date: string | null;
  is_limited_csv_window: boolean;
}

export interface DashboardMetadata {
  fred_source_mode: string;
  last_fetched_utc: string | null;
  as_of_date: string | null;
  credit_history: CreditHistoryMeta;
  refresh_errors: string[];
}

export interface DashboardSummary {
  growth_macro_score: number;
  score_1w_delta: number | null;
  score_1m_delta: number | null;
  regime: RegimeInfo;
  early_warning_tech: EarlyWarningTech;
  credit_priority_buy: boolean;
  sahm: number | null;
}

export interface BaseModule {
  id: string;
  number: number;
  title: string;
  subtitle: string;
  weight: number;
  score: number | null;
  interpretation: string;
}

export interface LiquidityPoint {
  date: string;
  net_liquidity_bn: number | null;
  roc_3m_pct: number | null;
  nfci: number | null;
  score: number | null;
}

export interface LiquidityModuleData extends BaseModule {
  id: "liquidity";
  kpis: {
    net_liquidity_bn: number | null;
    net_liq_roc_3m_pct: number | null;
    net_liq_chg_3m_bn: number | null;
    nfci: number | null;
    walcl_bn: number | null;
    tga_bn: number | null;
    rrp_bn: number | null;
  };
  series: LiquidityPoint[];
}

export interface RealRatesPoint {
  date: string;
  dfii10: number | null;
  chg_3m_bp: number | null;
  t10y2y: number | null;
  sahm: number | null;
  score: number | null;
}

export interface RealRatesModuleData extends BaseModule {
  id: "real_rates";
  cycle_label: string;
  kpis: {
    dfii10: number | null;
    dfii10_chg_1m_bp: number | null;
    dfii10_chg_3m_bp: number | null;
    t10y2y: number | null;
    sahm: number | null;
  };
  series: RealRatesPoint[];
}

export interface TechExtensionPoint {
  date: string;
  qqq_dist: number | null;
  smh_dist: number | null;
  iwf_iwd_0_100: number | null;
  score: number | null;
}

export interface TechExtensionModuleData extends BaseModule {
  id: "tech_extension";
  kpis: {
    qqq_dist_sma200_pct: number | null;
    smh_dist_sma200_pct: number | null;
    iwf_iwd_2y_minmax: number | null;
    qqq_price: number | null;
    smh_price: number | null;
  };
  series: TechExtensionPoint[];
}

export interface MarketBreadthPoint {
  date: string;
  rsp_spy: number | null;
  rsp_spy_sma200: number | null;
  qqqe_qqq: number | null;
  qqqe_qqq_sma200: number | null;
  pct_sectors: number | null;
}

export interface MarketBreadthModuleData extends BaseModule {
  id: "market_breadth";
  bearish_divergence: boolean;
  kpis: {
    pct_sectors_above_sma200: number | null;
    sectors_above: number;
    sectors_total: number;
    rsp_spy_roc_3m_pct: number | null;
    qqqe_qqq_roc_3m_pct: number | null;
    rsp_spy_base100: number | null;
    qqqe_qqq_base100: number | null;
  };
  series: MarketBreadthPoint[];
}

export interface VolatilityPoint {
  date: string;
  vxn: number | null;
  vix_term_ratio: number | null;
  score: number | null;
}

export interface VolatilityModuleData extends BaseModule {
  id: "volatility";
  kpis: {
    vxn: number | null;
    vix: number | null;
    vix3m: number | null;
    vix_term_ratio: number | null;
  };
  series: VolatilityPoint[];
}

export interface CreditSparkPoint {
  date: string;
  value_bp: number | null;
}

export interface CreditSpreadCard {
  label: string;
  value_bp: number | null;
  chg_1m_bp: number | null;
  chg_3m_bp: number | null;
  percentile: number | null;
  tighter_than_pct: number | null;
  median_bp: number | null;
  buy_threshold_bp: number;
  status: {
    level: "normal" | "buy" | "watch" | "tight" | "neutral" | string;
    text: string;
  };
  series: CreditSparkPoint[];
}

export interface PriceOfRiskModuleData extends BaseModule {
  id: "price_of_risk";
  priority_buy_alert: boolean;
  window_label: string;
  is_limited_csv_window: boolean;
  hy: CreditSpreadCard;
  bbb: CreditSpreadCard;
}

export interface CyclicalsPoint {
  date: string;
  ma5: number | null;
  raw: number | null;
  xlk_xlp_pct: number | null;
}

export interface CyclicalsModuleData extends BaseModule {
  id: "cyclicals_defensives";
  kpis: {
    raw_0_100: number | null;
    ma5_0_100: number | null;
    xlk_xlp_2y_pct: number | null;
  };
  series: CyclicalsPoint[];
}

export type AnyModuleData =
  | LiquidityModuleData
  | RealRatesModuleData
  | TechExtensionModuleData
  | MarketBreadthModuleData
  | VolatilityModuleData
  | PriceOfRiskModuleData
  | CyclicalsModuleData;

export interface DashboardPayload {
  as_of_date: string;
  metadata: DashboardMetadata;
  summary: DashboardSummary;
  modules: AnyModuleData[];
}

export interface BacktestZoneStats {
  days: number;
  episodes: number;
  avg_fwd_3m_pct: number | null;
  avg_fwd_6m_pct: number | null;
}

export interface BacktestPoint {
  date: string;
  price: number | null;
  score: number | null;
  tech_early_warning: boolean;
  signal: "red" | "green" | null;
  red_marker: number | null;
  green_marker: number | null;
}

export interface BacktestPayload {
  ticker: "QQQ" | "SMH" | "SPY";
  years: number;
  start_date: string;
  end_date: string;
  stats: {
    red_zone: BacktestZoneStats;
    euphoria_score_only: BacktestZoneStats;
    tech_early_warning: BacktestZoneStats;
    green_zone: BacktestZoneStats;
    baseline: BacktestZoneStats;
  };
  series: BacktestPoint[];
}
