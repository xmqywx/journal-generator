import { useState } from 'react';
import type { StrategyResult } from '../../types';
import { formatCurrency, formatNumber, formatDateTime } from '../../utils/formatters';

interface TradeLogTableProps {
  strategies: StrategyResult[];
}

export function TradeLogTable({ strategies }: TradeLogTableProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="bg-white border border-border rounded-lg shadow-sm p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">交易记录</h3>
      <div className="space-y-2">
        {strategies.map((s) => (
          <div key={s.name} className="border border-border/50 rounded-lg">
            <button
              onClick={() => setExpanded(expanded === s.name ? null : s.name)}
              className="w-full flex items-center justify-between p-3 text-sm hover:bg-surface/50 rounded-lg"
            >
              <span className="font-medium text-text-primary">{s.name}</span>
              <span className="text-text-secondary">
                {s.trades.length} 笔交易
                <span className="ml-2">{expanded === s.name ? '\u25B2' : '\u25BC'}</span>
              </span>
            </button>
            {expanded === s.name && (
              <div className="px-3 pb-3">
                <div className="overflow-x-auto max-h-64 overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-white">
                      <tr className="border-b border-border">
                        <th className="text-left py-1.5 px-2 text-text-secondary font-medium">#</th>
                        <th className="text-left py-1.5 px-2 text-text-secondary font-medium">方向</th>
                        <th className="text-right py-1.5 px-2 text-text-secondary font-medium">入场价</th>
                        <th className="text-right py-1.5 px-2 text-text-secondary font-medium">出场价</th>
                        <th className="text-right py-1.5 px-2 text-text-secondary font-medium">数量</th>
                        <th className="text-right py-1.5 px-2 text-text-secondary font-medium">盈亏</th>
                        <th className="text-right py-1.5 px-2 text-text-secondary font-medium">时间</th>
                      </tr>
                    </thead>
                    <tbody>
                      {s.trades.map((t, i) => (
                        <tr key={i} className="border-b border-border/30 hover:bg-surface/30">
                          <td className="py-1.5 px-2 text-text-secondary">{i + 1}</td>
                          <td className={`py-1.5 px-2 font-medium ${t.side === 'long' ? 'text-profit' : 'text-loss'}`}>
                            {t.side === 'long' ? '做多' : '做空'}
                          </td>
                          <td className="py-1.5 px-2 text-right font-mono">{formatCurrency(t.entry_price)}</td>
                          <td className="py-1.5 px-2 text-right font-mono">{formatCurrency(t.exit_price)}</td>
                          <td className="py-1.5 px-2 text-right font-mono">{formatNumber(t.size, 6)}</td>
                          <td className={`py-1.5 px-2 text-right font-mono ${t.pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                            {formatCurrency(t.pnl)}
                          </td>
                          <td className="py-1.5 px-2 text-right text-text-secondary">
                            {t.entry_time ? formatDateTime(t.entry_time) : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
