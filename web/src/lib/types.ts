export interface PresetParam {
  name: string;
  default: number;
  description: string;
}

export interface PresetInfo {
  slug: string;
  name: string;
  description: string;
  params: PresetParam[];
}

export interface SummaryStats {
  strategy_name: string;
  session_count: number;
  win_rate: number;
  bust_rate: number;
  stop_win_rate: number;
  stop_loss_rate: number;
  time_limit_rate: number;
  mean_pnl: number;
  median_pnl: number;
  std_pnl: number;
  percentile_5: number;
  percentile_10: number;
  percentile_25: number;
  percentile_75: number;
  percentile_90: number;
  percentile_95: number;
  mean_rolls: number;
  mean_drawdown: number;
  avg_win: number;
  avg_loss: number;
}

export interface EquityPercentiles {
  rolls: number[];
  p5: number[];
  p25: number[];
  p50: number[];
  p75: number[];
  p95: number[];
}

export interface ChartData {
  pnl_values: number[];
  drawdown_values: number[];
  equity_percentiles: EquityPercentiles;
  equity_sample: number[][];
}

export interface SimulateResponse {
  summary: SummaryStats;
  charts: ChartData;
}

export interface CompareResponse {
  results: SimulateResponse[];
}

export interface SimulateRequest {
  strategy: string;
  bankroll: number;
  hours: number;
  rolls_per_hour: number;
  stop_win: number | null;
  stop_loss: number | null;
  sessions: number;
}

export interface CompareRequest {
  strategies: string[];
  bankroll: number;
  hours: number;
  rolls_per_hour: number;
  stop_win: number | null;
  stop_loss: number | null;
  sessions: number;
}
