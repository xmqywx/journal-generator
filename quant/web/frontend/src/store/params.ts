import { create } from 'zustand';
import type { BacktestRequest } from '../types';

interface ParamStore {
  params: BacktestRequest;
  setParam: <K extends keyof BacktestRequest>(key: K, value: BacktestRequest[K]) => void;
  setStrategyParam: (
    strategy: 'ema_triple' | 'vwap_ema' | 'ichimoku' | 'dynamic_grid' | 'random_monkey',
    key: string,
    value: number | boolean
  ) => void;
}

export const useParamStore = create<ParamStore>((set) => ({
  params: {
    symbol: 'BTC-USDT',
    timeframe: '1H',
    lookback_days: 365,
    data_source: 'okx',
    initial_capital: 690,
    fee_rate: 0.0005,
    strategies: {
      ema_triple: { enabled: true, leverage: 2, stop_loss: 0.03 },
      vwap_ema: { enabled: true, leverage: 2, stop_loss: 0.03 },
      ichimoku: { enabled: true, leverage: 2, stop_loss: 0.03 },
      dynamic_grid: { enabled: true, atr_period: 14, base_spacing: 0.02, atr_multiplier: 1.0, levels: 7, leverage: 2, stop_loss: 0.05 },
      random_monkey: { enabled: true, seed: 0, buy_prob: 0.30, sell_prob: 0.30, leverage: 2, stop_loss: 0.03 },
    },
  },
  setParam: (key, value) =>
    set((state) => ({ params: { ...state.params, [key]: value } })),
  setStrategyParam: (strategy, key, value) =>
    set((state) => ({
      params: {
        ...state.params,
        strategies: {
          ...state.params.strategies,
          [strategy]: { ...state.params.strategies[strategy], [key]: value },
        },
      },
    })),
}));
