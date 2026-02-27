import { useBacktest } from '../../hooks/useBacktest';
import { useCandles } from '../../hooks/useCandles';
import { useParamStore } from '../../store/params';
import { MetricsRow } from '../cards/MetricsRow';
import { CandlestickChart } from '../charts/CandlestickChart';
import { EquityCurve } from '../charts/EquityCurve';
import { DrawdownChart } from '../charts/DrawdownChart';
import { ReturnBarChart } from '../charts/ReturnBarChart';
import { StrategyTable } from '../tables/StrategyTable';
import { TradeLogTable } from '../tables/TradeLogTable';

export function MainContent() {
  const params = useParamStore((s) => s.params);
  const { data: backtestData, isLoading, isFetching, isPlaceholderData, error } = useBacktest();
  const { data: candles, isLoading: candlesLoading, isFetching: candlesFetching } = useCandles();

  const hasData = backtestData && backtestData.strategies.length > 0;
  const showLoading = isLoading || (isFetching && !hasData);

  return (
    <main className="flex-1 bg-surface overflow-y-auto h-screen">
      {/* 顶部栏 */}
      <div className="bg-white border-b border-border px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sm font-semibold text-text-primary">{params.symbol}</span>
          <span className="text-xs text-text-secondary px-2 py-0.5 bg-surface rounded">{params.timeframe}</span>
          <span className="text-xs text-text-secondary px-2 py-0.5 bg-surface rounded">{params.data_source.toUpperCase()}</span>
          <span className="text-xs text-text-secondary">回溯 {params.lookback_days} 天</span>
        </div>
        <div className="flex items-center gap-2">
          {(isLoading || isFetching) && (
            <div className="flex items-center gap-2 text-xs text-primary font-medium">
              <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              {isPlaceholderData ? '切换中...' : '计算中...'}
            </div>
          )}
          {error && !isFetching && (
            <span className="text-xs text-loss font-medium">请求失败: {(error as Error).message}</span>
          )}
        </div>
      </div>

      {/* 内容区 */}
      <div className="p-6 space-y-4 relative">
        {/* 数据切换遮罩 */}
        {isFetching && isPlaceholderData && hasData && (
          <div className="absolute inset-0 bg-white/60 z-10 flex items-center justify-center">
            <div className="flex items-center gap-3 bg-white px-6 py-3 rounded-lg shadow-md border border-border">
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-text-primary font-medium">正在加载 {params.symbol} 数据...</span>
            </div>
          </div>
        )}

        {hasData && (
          <>
            <MetricsRow strategies={backtestData.strategies} />

            {candles && candles.length > 0 && (
              <div className="relative">
                {candlesFetching && !candlesLoading && (
                  <div className="absolute top-3 right-3 z-10 flex items-center gap-2 bg-white/90 px-3 py-1.5 rounded-md border border-border text-xs text-text-secondary">
                    <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    更新K线...
                  </div>
                )}
                <CandlestickChart candles={candles} />
              </div>
            )}
            {candlesLoading && !candles && (
              <div className="bg-white border border-border rounded-lg shadow-sm p-4 h-[432px] flex items-center justify-center">
                <div className="flex items-center gap-2 text-sm text-text-secondary">
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  加载行情数据...
                </div>
              </div>
            )}

            <EquityCurve strategies={backtestData.strategies} timestamps={backtestData.timestamps} />

            <div className="grid grid-cols-2 gap-4">
              <ReturnBarChart strategies={backtestData.strategies} />
              <StrategyTable strategies={backtestData.strategies} />
            </div>

            <DrawdownChart strategies={backtestData.strategies} timestamps={backtestData.timestamps} />

            <TradeLogTable strategies={backtestData.strategies} />
          </>
        )}

        {showLoading && !hasData && (
          <div className="flex items-center justify-center h-96">
            <div className="flex items-center gap-3">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-text-secondary">正在加载数据...</span>
            </div>
          </div>
        )}

        {error && !isFetching && !hasData && (
          <div className="flex items-center justify-center h-96">
            <div className="text-center space-y-2">
              <p className="text-loss text-sm font-medium">请求失败</p>
              <p className="text-text-secondary text-xs">{(error as Error).message}</p>
            </div>
          </div>
        )}

        {!backtestData && !isLoading && !isFetching && !error && (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <p className="text-text-secondary text-sm">调整左侧参数开始回测</p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
