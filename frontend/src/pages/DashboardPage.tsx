import { useState } from 'react'
import {
  Activity,
  AlertTriangle,
  Server,
  ShieldAlert,
  WifiOff,
  Bot,
  Shield,
} from 'lucide-react'
import { Layout } from '@/components/layout/Layout'
import { StatCard } from '@/components/cards/StatCard'
import { AgentStatusCard } from '@/components/cards/AgentStatusCard'
import { IncidentsTimeline } from '@/components/charts/IncidentsTimeline'
import { SeverityPie } from '@/components/charts/SeverityPie'
import { Badge } from '@/components/ui/Badge'
import { Empty } from '@/components/ui/Empty'
import { usePolling } from '@/hooks/usePolling'
import { useWebSocket } from '@/hooks/useWebSocket'
import { statsApi } from '@/api/stats'
import { agentsApi } from '@/api/agents'
import { incidentsApi } from '@/api/incidents'
import type { AgentNetvigie, Incident, OverviewStats, TimeSeriesPoint } from '@/types'

export function DashboardPage() {
  const [stats, setStats] = useState<OverviewStats | null>(null)
  const [agents, setAgents] = useState<AgentNetvigie[]>([])
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [series, setSeries] = useState<TimeSeriesPoint[]>([])
  const [toasts, setToasts] = useState<Array<{ id: number; verdict: string; host: string }>>([])

  const refresh = async () => {
    try {
      const [s, a, inc, ts] = await Promise.all([
        statsApi.overview(),
        agentsApi.netvigie(),
        incidentsApi.list({ page_size: 5 }),
        statsApi.timeseries('events', 60),
      ])
      setStats(s)
      setAgents(a)
      setIncidents(inc.items)
      setSeries(ts.series)
    } catch (e) {
      console.error(e)
    }
  }

  usePolling(refresh, 8000)

  const { connected } = useWebSocket((msg) => {
    if (msg.type === 'incident') {
      const d = msg.data as { verdict?: string; hostname?: string; incident_id?: string }
      const id = Date.now()
      setToasts((t) => [
        ...t,
        { id, verdict: d.verdict || 'INCIDENT', host: d.hostname || '?' },
      ])
      setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000)
      refresh()
    }
  })

  return (
    <Layout title="Tableau de bord">
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.verdict === 'NORMAL' ? 'success' : 'critical'}`}>
            <div className="title">🚨 Nouvel incident — {t.verdict}</div>
            <div className="desc">Machine : {t.host}</div>
          </div>
        ))}
      </div>

      <div className="cards-grid">
        <StatCard
          label="Machines supervisées"
          value={stats?.total_machines ?? '—'}
          sub={`${stats?.active_machines ?? 0} actives`}
          icon={Server}
        />
        <StatCard
          label="Machines injoignables"
          value={stats?.unreachable_machines ?? '—'}
          icon={WifiOff}
          color="#ef4444"
        />
        <StatCard
          label="Alertes (dernière heure)"
          value={stats?.alerts_last_hour ?? '—'}
          sub={`${stats?.critical_alerts ?? 0} critiques`}
          icon={ShieldAlert}
          color="#f59e0b"
        />
        <StatCard
          label="Incidents ouverts"
          value={stats?.open_incidents ?? '—'}
          sub={`${stats?.total_incidents ?? 0} au total`}
          icon={AlertTriangle}
          color="#dc2626"
        />
      </div>

      <div className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <h2>
              <Activity size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
              Événements (60 min)
            </h2>
            <Badge severity={connected ? 'low' : 'high'}>
              {connected ? 'Live' : 'Hors ligne'}
            </Badge>
          </div>
          {series.length > 0 ? (
            <IncidentsTimeline data={series} />
          ) : (
            <Empty message="Aucun événement" />
          )}
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Incidents par sévérité</h2>
          </div>
          <SeverityPie data={stats?.incidents_by_severity || {}} />
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>
            <Bot size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            État des 4 agents NETVIGIE
          </h2>
        </div>
        <div className="cards-grid" style={{ marginBottom: 0 }}>
          {agents.map((a) => (
            <AgentStatusCard key={a.id} agent={a} />
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Derniers incidents</h2>
          <a href="/incidents">Voir tout →</a>
        </div>
        {incidents.length > 0 ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Verdict</th>
                  <th>Sévérité</th>
                  <th>Confiance</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((inc) => (
                  <tr key={inc.id}>
                    <td>{new Date(inc.incident_ts).toLocaleString('fr-FR')}</td>
                    <td>
                      <Badge severity={inc.severity}>{inc.verdict}</Badge>
                    </td>
                    <td>
                      <Badge severity={inc.severity}>{inc.severity}</Badge>
                    </td>
                    <td>{Math.round(inc.confidence * 100)}%</td>
                    <td style={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {inc.title}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty message="Aucun incident détecté" />
        )}
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>
            <Shield size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            État Wazuh
          </h2>
        </div>
        <p style={{ fontSize: 13, color: '#9ca3af' }}>
          {stats?.wazuh_status === 'ok'
            ? '✅ Wazuh API opérationnelle'
            : '⚠ Wazuh non vérifié'}
        </p>
      </div>
    </Layout>
  )
}