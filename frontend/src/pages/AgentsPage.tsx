import { useState } from 'react'
import { Layout } from '@/components/layout/Layout'
import { AgentStatusCard } from '@/components/cards/AgentStatusCard'
import { Badge } from '@/components/ui/Badge'
import { Empty } from '@/components/ui/Empty'
import { usePolling } from '@/hooks/usePolling'
import { agentsApi } from '@/api/agents'
import type { AgentNetvigie, AgentWazuh } from '@/types'

export function AgentsPage() {
  const [agents, setAgents] = useState<AgentNetvigie[]>([])
  const [wazuhAgents, setWazuhAgents] = useState<AgentWazuh[]>([])

  const refresh = async () => {
    try {
      const [a, w] = await Promise.all([agentsApi.netvigie(), agentsApi.wazuh()])
      setAgents(a)
      setWazuhAgents(w)
    } catch (e) {
      console.error(e)
    }
  }

  usePolling(refresh, 5000)

  return (
    <Layout title="Agents">
      <div className="panel">
        <div className="panel-header">
          <h2>4 agents NETVIGIE</h2>
        </div>
        <div className="cards-grid" style={{ marginBottom: 0 }}>
          {agents.map((a) => (
            <AgentStatusCard key={a.id} agent={a} />
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Agents Wazuh</h2>
        </div>
        {wazuhAgents.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nom</th>
                <th>IP</th>
                <th>Version</th>
                <th>OS</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {wazuhAgents.map((a) => (
                <tr key={a.id}>
                  <td>{a.wazuh_id}</td>
                  <td>{a.name}</td>
                  <td>{a.ip}</td>
                  <td>{a.version || '—'}</td>
                  <td>{a.os_name || '—'}</td>
                  <td>
                    <span className={`status-dot ${a.status === 'active' ? 'active' : 'inactive'}`} />
                    {a.status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <Empty message="Aucun agent Wazuh" />
        )}
      </div>
    </Layout>
  )
}