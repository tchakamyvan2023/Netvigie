import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import type { TimeSeriesPoint } from '@/types'

export function IncidentsTimeline({ data }: { data: TimeSeriesPoint[] }) {
  const formatted = data.map((p) => ({
    time: new Date(p.timestamp).toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
    }),
    value: p.value,
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={formatted}>
        <defs>
          <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.6} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis dataKey="time" stroke="#9ca3af" fontSize={11} />
        <YAxis stroke="#9ca3af" fontSize={11} />
        <Tooltip
          contentStyle={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 6 }}
        />
        <Area type="monotone" dataKey="value" stroke="#3b82f6" fill="url(#colorValue)" />
      </AreaChart>
    </ResponsiveContainer>
  )
}