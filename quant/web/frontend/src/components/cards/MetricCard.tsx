interface MetricCardProps {
  label: string;
  value: string;
  subValue?: string;
  color?: 'default' | 'profit' | 'loss';
}

export function MetricCard({ label, value, subValue, color = 'default' }: MetricCardProps) {
  const colorClass = color === 'profit' ? 'text-profit' : color === 'loss' ? 'text-loss' : 'text-text-primary';
  
  return (
    <div className="bg-white border border-border rounded-lg p-4 shadow-sm">
      <div className="text-xs font-medium text-text-secondary uppercase tracking-wider">{label}</div>
      <div className={`text-xl font-semibold font-mono mt-1 ${colorClass}`}>{value}</div>
      {subValue && <div className="text-xs text-text-secondary mt-0.5 font-mono">{subValue}</div>}
    </div>
  );
}
