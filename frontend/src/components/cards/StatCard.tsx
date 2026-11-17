import { LucideIcon } from 'lucide-react'

interface Props {
  label: string
  value: string | number
  sub?: string
  icon?: LucideIcon
  color?: string
}

export function StatCard({ label, value, sub, icon: Icon, color }: Props) {
  return (
    <div className="stat-card">
      <div className="label">
        {Icon && <Icon size={14} />}
        {label}
      </div>
      <div className="value" style={color ? { color } : undefined}>
        {value}
      </div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  )
}