import { Bot } from 'lucide-react'
import type { AgentNetvigie } from '@/types'

export function AgentStatusCard({ agent }: { agent: AgentNetvigie }) {
  return (
    <div className="stat-card">
      <div className="label">
        <Bot size={14} />
        {agent.name.toUpperCase()}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
        <span className={`status-dot ${agent.status}`} />
        <span style={{ fontSize: 13, color: agent.status === 'running' ? '#10b981' : '#9ca3af' }}>
          {agent.status}
        </span>
      </div>
      <div className="sub" style={{ marginTop: 8 }}>
        {agent.events_processed} événements • {agent.errors_count} erreurs
      </div>
      <div className="sub">Moy. {agent.avg_processing_ms.toFixed(0)} ms</div>
    </div>
  )
}