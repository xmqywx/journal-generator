import client from './client';
import type { BacktestRequest, BacktestResponse, CandleData } from '../types';

export async function runBacktest(params: BacktestRequest): Promise<BacktestResponse> {
  // Transform nested strategies format to flat format expected by backend
  const { strategies, ...rest } = params;
  const payload = {
    ...rest,
    dual_ma: strategies.dual_ma,
    rsi: strategies.rsi,
    bollinger: strategies.bollinger,
    dynamic_grid: strategies.dynamic_grid,
    random_monkey: strategies.random_monkey,
  };
  const { data } = await client.post<BacktestResponse>('/backtest', payload);
  return data;
}

export async function fetchCandles(
  symbol: string,
  timeframe: string,
  lookback_days: number,
  data_source: string
): Promise<CandleData[]> {
  const { data } = await client.get<CandleData[]>('/candles', {
    params: { symbol, timeframe, lookback_days, data_source },
  });
  return data;
}
