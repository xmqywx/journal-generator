import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { StrategyResult } from '../../types';
import { formatPercent } from '../../utils/formatters';

interface ReturnBarChartProps {
  strategies: StrategyResult[];
}

export function ReturnBarChart({ strategies }: ReturnBarChartProps) {
  const data = strategies.map((s) => ({
    name: s.name,
    return: s.metrics.total_return,
  }));

  return (
    <div className="bg-white border border-border rounded-lg shadow-sm p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">策略收益</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} layout="vertical">
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: '#6B7280' }}
            tickLine={false}
            tickFormatter={(v) => `${v}%`}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11, fill: '#6B7280' }}
            tickLine={false}
            width={120}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #E5E7EB',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value) => [formatPercent(value as number), '收益']}
          />
          <Bar dataKey="return" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={index} fill={entry.return >= 0 ? '#16A34A' : '#DC2626'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
