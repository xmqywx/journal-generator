import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { StrategyResult } from '../../types';
import { formatPercent, formatTimestamp } from '../../utils/formatters';

const COLORS = ['#DC2626', '#F97316', '#EAB308'];

interface DrawdownChartProps {
  strategies: StrategyResult[];
  timestamps: number[];
}

function calcDrawdown(equityCurve: number[]): number[] {
  let peak = equityCurve[0] || 0;
  return equityCurve.map((eq) => {
    if (eq > peak) peak = eq;
    return peak > 0 ? ((eq - peak) / peak) * 100 : 0;
  });
}

export function DrawdownChart({ strategies, timestamps }: DrawdownChartProps) {
  const step = Math.max(1, Math.floor(timestamps.length / 500));

  const data = timestamps
    .filter((_, i) => i % step === 0 || i === timestamps.length - 1)
    .map((ts, idx) => {
      const origIdx = Math.min(idx * step, timestamps.length - 1);
      const point: Record<string, number | string> = {
        time: formatTimestamp(ts),
      };
      strategies.forEach((s) => {
        const dd = calcDrawdown(s.equity_curve);
        point[s.name] = dd[origIdx] ?? 0;
      });
      return point;
    });

  return (
    <div className="bg-white border border-border rounded-lg shadow-sm p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">回撤</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data}>
          <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#6B7280' }} tickLine={false} />
          <YAxis
            tick={{ fontSize: 11, fill: '#6B7280' }}
            tickLine={false}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #E5E7EB',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value) => [formatPercent(value as number), '']}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
          {strategies.map((s, i) => (
            <Area
              key={s.name}
              type="monotone"
              dataKey={s.name}
              stroke={COLORS[i % COLORS.length]}
              fill={COLORS[i % COLORS.length]}
              fillOpacity={0.1}
              strokeWidth={1.5}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
