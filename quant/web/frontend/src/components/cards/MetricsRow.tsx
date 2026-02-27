import { MetricCard } from './MetricCard';
import type { StrategyResult } from '../../types';
import { formatPercent, formatCurrency, formatNumber } from '../../utils/formatters';

interface MetricsRowProps {
  strategies: StrategyResult[];
}

export function MetricsRow({ strategies }: MetricsRowProps) {
  const totalInitial = strategies.reduce((sum, s) => sum + s.metrics.initial_capital, 0);
  const totalFinal = strategies.reduce((sum, s) => sum + s.metrics.final_equity, 0);
  const totalReturn = totalInitial > 0 ? ((totalFinal - totalInitial) / totalInitial) * 100 : 0;
  const bestSharpe = Math.max(...strategies.map((s) => s.metrics.sharpe_ratio));
  const worstDrawdown = Math.min(...strategies.map((s) => -Math.abs(s.metrics.max_drawdown)));
  const totalTrades = strategies.reduce((sum, s) => sum + s.metrics.total_trades, 0);
  const avgWinRate = strategies.length > 0
    ? strategies.reduce((sum, s) => sum + s.metrics.win_rate, 0) / strategies.length
    : 0;

  return (
    <div className="grid grid-cols-5 gap-3">
      <MetricCard
        label="组合净值"
        value={formatCurrency(totalFinal)}
        subValue={`初始 ${formatCurrency(totalInitial)}`}
        color={totalFinal >= totalInitial ? 'profit' : 'loss'}
      />
      <MetricCard
        label="总收益率"
        value={formatPercent(totalReturn)}
        color={totalReturn >= 0 ? 'profit' : 'loss'}
      />
      <MetricCard
        label="最佳夏普"
        value={formatNumber(bestSharpe, 3)}
        subValue={strategies.find(s => s.metrics.sharpe_ratio === bestSharpe)?.name}
      />
      <MetricCard
        label="最大回撤"
        value={formatPercent(worstDrawdown)}
        color="loss"
      />
      <MetricCard
        label="总交易数"
        value={totalTrades.toString()}
        subValue={`平均胜率 ${formatPercent(avgWinRate)}`}
      />
    </div>
  );
}
