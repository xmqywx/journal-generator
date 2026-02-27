import { useQuery } from '@tanstack/react-query';
import { runBacktest } from '../api/backtest';
import { useParamStore } from '../store/params';
import { useDebounce } from './useDebounce';

export function useBacktest() {
  const params = useParamStore((s) => s.params);
  const debouncedParams = useDebounce(params, 500);

  return useQuery({
    queryKey: ['backtest', debouncedParams],
    queryFn: () => runBacktest(debouncedParams),
    staleTime: 60_000,
    retry: 1,
    retryDelay: 1000,
    placeholderData: (prev) => prev,
    refetchOnWindowFocus: false,
  });
}
