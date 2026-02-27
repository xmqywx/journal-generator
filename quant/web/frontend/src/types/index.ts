export interface BacktestRequest {
  symbol: string;
  timeframe: string;
  lookback_days: number;
  data_source: string;
  initial_capital: number;
  fee_rate: number;
  strategies: {
    dual_ma: { enabled: boolean; fast: number; slow: number; leverage: number; stop_loss: number };
    rsi: { enabled: boolean; period: number; oversold: number; overbought: number; leverage: number; stop_loss: number };
    bollinger: { enabled: boolean; period: number; num_std: number; leverage: number; stop_loss: number };
    dynamic_grid: { enabled: boolean; atr_period: number; base_spacing: number; atr_multiplier: number; levels: number; leverage: number; stop_loss: number };
    random_monkey: { enabled: boolean; seed: number; buy_prob: number; sell_prob: number; stop_loss: number };
  };
}

export interface TradeResult {
  entry_price: number;
  exit_price: number;
  size: number;
  side: string;
  pnl: number;
  entry_time: number;
  exit_time: number;
}

export interface StrategyMetrics {
  initial_capital: number;
  final_equity: number;
  total_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  total_trades: number;
  avg_pnl: number;
}

export interface StrategyResult {
  name: string;
  equity_curve: number[];
  metrics: StrategyMetrics;
  trades: TradeResult[];
}

export interface BacktestResponse {
  strategies: StrategyResult[];
  timestamps: number[];
}

export interface CandleData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}
