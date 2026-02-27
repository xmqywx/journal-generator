import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { StrategyResult } from '../../types';
import { formatCurrency, formatTimestamp } from '../../utils/formatters';

const COLORS = ['#2563EB', '#16A34A', '#F59E0B', '#8B5CF6', '#EC4899'];

interface EquityCurveProps {
  strategies: StrategyResult[];
  timestamps: number[];
}

export function EquityCurve({ strategies, timestamps }: EquityCurveProps) {
  // Sample data points for performance (max 500 points)
  const step = Math.max(1, Math.floor(timestamps.length / 500));
  
  const data = timestamps
    .filter((_, i) => i % step === 0 || i === timestamps.length - 1)
    .map((ts, idx) => {
      const origIdx = Math.min(idx * step, timestamps.length - 1);
      const point: Record<string, number | string> = {
        time: formatTimestamp(ts),
        timestamp: ts,
      };
      strategies.forEach((s) => {
        point[s.name] = s.equity_curve[origIdx] ?? 0;
      });
      return point;
    });

  return (
    <div className="bg-white border border-border rounded-lg shadow-sm p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">权益曲线</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#6B7280' }} tickLine={false} />
          <YAxis
            tick={{ fontSize: 11, fill: '#6B7280' }}
            tickLine={false}
            tickFormatter={(v) => `$${v}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #E5E7EB',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value) => [formatCurrency(value as number), '']}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
          {strategies.map((s, i) => (
            <Line
              key={s.name}
              type="monotone"
              dataKey={s.name}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
