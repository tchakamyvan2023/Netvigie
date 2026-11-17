import { useState } from 'react'
import { Layout } from '@/components/layout/Layout'
import { Badge } from '@/components/ui/Badge'
import { Empty } from '@/components/ui/Empty'
import { usePolling } from '@/hooks/usePolling'
import { eventsApi } from '@/api/events'
import type { Event, Page } from '@/types'

export function LogsPage() {
  const [data, setData] = useState<Page<Event> | null>(null)
  const [source, setSource] = useState('')
  const [severity, setSeverity] = useState('')
  const [eventType, setEventType] = useState('')

  const refresh = async () => {
    try {
      const res = await eventsApi.list({
        page_size: 200,
        source: source || undefined,
        severity: severity || undefined,
        event_type: eventType || undefined,
      })
      setData(res)
    } catch (e) {
      console.error(e)
    }
  }

  usePolling(refresh, 4000)

  return (
    <Layout title="Centre de logs">
      <div className="filters">
        <select className="select" value={source} onChange={(e) => setSource(e.target.value)}>
          <option value="">Toutes sources</option>
          <option value="wazuh">Wazuh</option>
          <option value="collector">Collector</option>
          <option value="diagnostic">Diagnostic</option>
          <option value="security">Security</option>
          <option value="correlation">Correlation</option>
        </select>
        <select className="select" value={eventType} onChange={(e) => setEventType(e.target.value)}>
          <option value="">Tous types</option>
          <option value="machine_metric">Machine metric</option>
          <option value="network_anomaly">Network anomaly</option>
          <option value="security_incident">Security incident</option>
          <option value="incident_created">Incident created</option>
        </select>
        <select className="select" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">Toutes sévérités</option>
          <option value="info">Info</option>
          <option value="low">Basse</option>
          <option value="medium">Moyenne</option>
          <option value="high">Haute</option>
          <option value="critical">Critique</option>
        </select>
      </div>

      <div className="panel">
        {data && data.items.length > 0 ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Source</th>
                  <th>Type</th>
                  <th>Sévérité</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((e) => (
                  <tr key={e.id}>
                    <td>{new Date(e.event_ts).toLocaleString('fr-FR')}</td>
                    <td>{e.source}</td>
                    <td>{e.event_type}</td>
                    <td><Badge severity={e.severity}>{e.severity}</Badge></td>
                    <td style={{ maxWidth: 500, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {e.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty message="Aucun événement" />
        )}
      </div>
    </Layout>
  )
}