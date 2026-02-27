import { useQuery } from '@tanstack/react-query';
import { fetchCandles } from '../api/backtest';
import { useParamStore } from '../store/params';
import { useDebounce } from './useDebounce';

export function useCandles() {
  const { symbol, timeframe, lookback_days, data_source } = useParamStore((s) => s.params);
  const debouncedSymbol = useDebounce(symbol, 500);
  const debouncedTimeframe = useDebounce(timeframe, 500);
  const debouncedLookback = useDebounce(lookback_days, 500);
  const debouncedSource = useDebounce(data_source, 500);

  return useQuery({
    queryKey: ['candles', debouncedSymbol, debouncedTimeframe, debouncedLookback, debouncedSource],
    queryFn: () => fetchCandles(debouncedSymbol, debouncedTimeframe, debouncedLookback, debouncedSource),
    staleTime: 300_000,
    retry: 1,
    retryDelay: 1000,
    placeholderData: (prev) => prev,
    refetchOnWindowFocus: false,
  });
}
