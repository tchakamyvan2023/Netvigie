import { LogOut } from 'lucide-react'
import { useAuth } from '@/auth/AuthContext'

export function Topbar({ title }: { title: string }) {
  const { user, logout } = useAuth()
  return (
    <div className="topbar">
      <h1>{title}</h1>
      <div className="user">
        <span>
          {user?.username} <span style={{ color: '#3b82f6' }}>({user?.role})</span>
        </span>
        <button className="btn" onClick={logout} title="Déconnexion">
          <LogOut size={16} />
        </button>
      </div>
    </div>
  )
}