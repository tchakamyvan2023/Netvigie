import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Server,
  AlertTriangle,
  FileText,
  Bot,
  Shield,
} from 'lucide-react'

const links = [
  { to: '/', label: 'Tableau de bord', icon: LayoutDashboard },
  { to: '/machines', label: 'Machines', icon: Server },
  { to: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { to: '/logs', label: 'Logs', icon: FileText },
  { to: '/agents', label: 'Agents', icon: Bot },
]

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <Shield size={20} color="#3b82f6" />
        <span>NETVIGIE</span>
      </div>
      <nav>
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.to === '/'}>
            <l.icon size={18} />
            <span>{l.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="footer">v1.0.0 — SOC</div>
    </aside>
  )
}