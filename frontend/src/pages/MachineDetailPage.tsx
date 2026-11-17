import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Layout } from '@/components/layout/Layout'
import { Badge } from '@/components/ui/Badge'
import { Empty } from '@/components/ui/Empty'
import { machinesApi } from '@/api/machines'
import { eventsApi } from '@/api/events'
import { alertsApi } from '@/api/alerts'
import type { Alert, Event, Machine } from '@/types'

type Tab = 'general' | 'perf' | 'network' | 'events' | 'alerts'

export function MachineDetailPage() {
  const { id } = useParams()
  const [machine, setMachine] = useState<Machine | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [tab, setTab] = useState<Tab>('general')

  useEffect(() => {
    if (!id) return
    const nid = Number(id)
    machinesApi.get(nid).then(setMachine).catch(console.error)
    eventsApi
      .list({ machine_id: nid, page_size: 50 })
      .then((r) => setEvents(r.items))
      .catch(console.error)
  }, [id])

  useEffect(() => {
    if (!machine?.agent_id) return
    alertsApi
      .list({ agent_id: machine.agent_id, page_size: 50 })
      .then((r) => setAlerts(r.items))
      .catch(console.error)
  }, [machine?.agent_id])

  if (!machine) return <Layout title="Machine"><Empty message="Chargement..." /></Layout>

  return (
    <Layout title={machine.hostname}>
      <Link to="/machines" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 16 }}>
        <ArrowLeft size={16} /> Retour aux machines
      </Link>

      <div className="tabs">
        {(['general', 'perf', 'network', 'events', 'alerts'] as Tab[]).map((t) => (
          <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
            {t === 'general' && 'Vue générale'}
            {t === 'perf' && 'Performances'}
            {t === 'network' && 'Réseau'}
            {t === 'events' && `Événements (${events.length})`}
            {t === 'alerts' && `Alertes (${alerts.length})`}
          </button>
        ))}
      </div>

      <div className="panel">
        {tab === 'general' && (
          <div>
            <h2 style={{ marginBottom: 16 }}>{machine.hostname}</h2>
            <table>
              <tbody>
                <tr><td><strong>IP</strong></td><td>{machine.ip}</td></tr>
                <tr><td><strong>Agent ID</strong></td><td>{machine.agent_id || '—'}</td></tr>
                <tr><td><strong>OS</strong></td><td>{machine.os_name} {machine.os_version}</td></tr>
                <tr><td><strong>Kernel</strong></td><td>{machine.kernel || '—'}</td></tr>
                <tr><td><strong>CPU</strong></td><td>{machine.cpu_name} ({machine.cpu_cores} cores)</td></tr>
                <tr><td><strong>RAM</strong></td><td>{machine.ram_total_mb} Mo</td></tr>
                <tr><td><strong>Rôle</strong></td><td>{machine.role || '—'}</td></tr>
                <tr><td><strong>Criticité</strong></td><td>{machine.criticality || '—'}</td></tr>
                <tr><td><strong>Statut</strong></td><td><Badge severity={machine.status === 'active' ? 'low' : 'high'}>{machine.status}</Badge></td></tr>
                <tr><td><strong>Exclue</strong></td><td>{machine.is_excluded ? 'Oui' : 'Non'}</td></tr>
              </tbody>
            </table>
          </div>
        )}

        {tab === 'perf' && (
          <div>
            <h3 style={{ marginBottom: 12 }}>Utilisation</h3>
            <p>RAM : {machine.ram_usage_percent ?? 0}%</p>
            <p>Disque : {machine.disk_usage_percent ?? 0}%</p>
          </div>
        )}

        {tab === 'network' && (
          <div>
            <p><strong>Latence</strong> : {machine.latency_ms ?? '—'} ms</p>
            <p><strong>Pertes</strong> : {machine.packet_loss_percent ?? '—'} %</p>
            <p><strong>Dernier ping</strong> : {machine.last_seen || '—'}</p>
          </div>
        )}

        {tab === 'events' && (
          events.length > 0 ? (
            <table>
              <thead><tr><th>Date</th><th>Type</th><th>Sévérité</th><th>Description</th></tr></thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.id}>
                    <td>{new Date(e.event_ts).toLocaleString('fr-FR')}</td>
                    <td>{e.event_type}</td>
                    <td><Badge severity={e.severity}>{e.severity}</Badge></td>
                    <td>{e.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Empty message="Aucun événement" />
        )}

        {tab === 'alerts' && (
          alerts.length > 0 ? (
            <table>
              <thead><tr><th>Date</th><th>Règle</th><th>Niveau</th><th>Description</th></tr></thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.id}>
                    <td>{new Date(a.alert_ts).toLocaleString('fr-FR')}</td>
                    <td>{a.rule_id}</td>
                    <td><Badge severity={a.severity}>L{a.rule_level}</Badge></td>
                    <td>{a.rule_description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Empty message="Aucune alerte" />
        )}
      </div>
    </Layout>
  )
}