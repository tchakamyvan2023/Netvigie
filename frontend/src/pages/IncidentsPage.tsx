import { useState } from 'react'
import { Layout } from '@/components/layout/Layout'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Empty } from '@/components/ui/Empty'
import { usePolling } from '@/hooks/usePolling'
import { incidentsApi } from '@/api/incidents'
import type { Incident, Page } from '@/types'

export function IncidentsPage() {
  const [data, setData] = useState<Page<Incident> | null>(null)
  const [verdict, setVerdict] = useState('')
  const [severity, setSeverity] = useState('')
  const [status, setStatus] = useState('')

  const refresh = async () => {
    try {
      const res = await incidentsApi.list({
        page_size: 100,
        verdict: verdict || undefined,
        severity: severity || undefined,
        status: status || undefined,
      })
      setData(res)
    } catch (e) {
      console.error(e)
    }
  }

  usePolling(refresh, 5000)

  const onStatusChange = async (inc: Incident, newStatus: string) => {
    try {
      await incidentsApi.updateStatus(inc.id, newStatus)
      refresh()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <Layout title="Incidents">
      <div className="filters">
        <select className="select" value={verdict} onChange={(e) => setVerdict(e.target.value)}>
          <option value="">Tous les verdicts</option>
          <option value="NORMAL">NORMAL</option>
          <option value="TECHNICAL_ANOMALY">TECHNICAL_ANOMALY</option>
          <option value="NETWORK_FAILURE">NETWORK_FAILURE</option>
          <option value="SECURITY_ALERT">SECURITY_ALERT</option>
          <option value="SUSPECTED_ATTACK">SUSPECTED_ATTACK</option>
          <option value="MIXED_INCIDENT">MIXED_INCIDENT</option>
          <option value="INVESTIGATION_REQUIRED">INVESTIGATION_REQUIRED</option>
        </select>
        <select className="select" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">Toutes sévérités</option>
          <option value="critical">Critique</option>
          <option value="high">Haute</option>
          <option value="medium">Moyenne</option>
          <option value="low">Basse</option>
        </select>
        <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Tous statuts</option>
          <option value="new">Nouveau</option>
          <option value="acknowledged">Acquitté</option>
          <option value="investigating">En investigation</option>
          <option value="resolved">Résolu</option>
          <option value="false_positive">Faux positif</option>
        </select>
      </div>

      <div className="panel">
        {data && data.items.length > 0 ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Verdict</th>
                  <th>Sévérité</th>
                  <th>Confiance</th>
                  <th>Titre</th>
                  <th>Statut</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((inc) => (
                  <tr key={inc.id}>
                    <td>{new Date(inc.incident_ts).toLocaleString('fr-FR')}</td>
                    <td><Badge severity={inc.severity}>{inc.verdict}</Badge></td>
                    <td><Badge severity={inc.severity}>{inc.severity}</Badge></td>
                    <td>{Math.round(inc.confidence * 100)}%</td>
                    <td style={{ maxWidth: 350, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {inc.title}
                    </td>
                    <td><Badge severity="neutral">{inc.status}</Badge></td>
                    <td>
                      {inc.status === 'new' && (
                        <Button onClick={() => onStatusChange(inc, 'acknowledged')}>
                          Acquitter
                        </Button>
                      )}
                      {inc.status === 'acknowledged' && (
                        <Button onClick={() => onStatusChange(inc, 'resolved')}>
                          Résoudre
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty message="Aucun incident" />
        )}
      </div>
    </Layout>
  )
}