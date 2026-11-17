import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const COLORS: Record<string, string> = {
  critical: '#dc2626',
  high: '#f59e0b',
  medium: '#3b82f6',
  low: '#10b981',
  info: '#06b6d4',
}

export function SeverityPie({ data }: { data: Record<string, number> }) {
  const formatted = Object.entries(data || {}).map(([k, v]) => ({
    name: k,
    value: v,
    color: COLORS[k] || '#6b7280',
  }))

  if (formatted.length === 0) {
    return <div className="empty">Aucune donnée</div>
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={formatted} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
          {formatted.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip contentStyle={{ background: '#111827', border: '1px solid #1f2937' }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  )
}