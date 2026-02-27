import type { StrategyResult } from '../../types';
import { formatPercent, formatCurrency, formatNumber } from '../../utils/formatters';

interface StrategyTableProps {
  strategies: StrategyResult[];
}

export function StrategyTable({ strategies }: StrategyTableProps) {
  return (
    <div className="bg-white border border-border rounded-lg shadow-sm p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">策略对比</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 px-3 text-text-secondary font-medium">策略</th>
              <th className="text-right py-2 px-3 text-text-secondary font-medium">收益率</th>
              <th className="text-right py-2 px-3 text-text-secondary font-medium">夏普</th>
              <th className="text-right py-2 px-3 text-text-secondary font-medium">最大回撤</th>
              <th className="text-right py-2 px-3 text-text-secondary font-medium">胜率</th>
              <th className="text-right py-2 px-3 text-text-secondary font-medium">交易数</th>
              <th className="text-right py-2 px-3 text-text-secondary font-medium">最终净值</th>
            </tr>
          </thead>
          <tbody>
            {strategies.map((s) => (
              <tr key={s.name} className="border-b border-border/50 hover:bg-surface/50">
                <td className="py-2 px-3 font-medium text-text-primary">{s.name}</td>
                <td className={`py-2 px-3 text-right font-mono ${s.metrics.total_return >= 0 ? 'text-profit' : 'text-loss'}`}>
                  {formatPercent(s.metrics.total_return)}
                </td>
                <td className="py-2 px-3 text-right font-mono text-text-primary">
                  {formatNumber(s.metrics.sharpe_ratio, 3)}
                </td>
                <td className="py-2 px-3 text-right font-mono text-loss">
                  {formatPercent(-Math.abs(s.metrics.max_drawdown))}
                </td>
                <td className="py-2 px-3 text-right font-mono text-text-primary">
                  {formatPercent(s.metrics.win_rate)}
                </td>
                <td className="py-2 px-3 text-right font-mono text-text-primary">
                  {s.metrics.total_trades}
                </td>
                <td className={`py-2 px-3 text-right font-mono ${s.metrics.final_equity >= s.metrics.initial_capital ? 'text-profit' : 'text-loss'}`}>
                  {formatCurrency(s.metrics.final_equity)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
