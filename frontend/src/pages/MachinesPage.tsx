import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'
import { Layout } from '@/components/layout/Layout'
import { Badge } from '@/components/ui/Badge'
import { Empty } from '@/components/ui/Empty'
import { usePolling } from '@/hooks/usePolling'
import { machinesApi } from '@/api/machines'
import type { Machine, Page } from '@/types'

export function MachinesPage() {
  const [data, setData] = useState<Page<Machine> | null>(null)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')

  const refresh = async () => {
    try {
      const res = await machinesApi.list({
        page_size: 100,
        search: search || undefined,
        status: status || undefined,
      })
      setData(res)
    } catch (e) {
      console.error(e)
    }
  }

  usePolling(refresh, 8000)

  return (
    <Layout title="Machines supervisées">
      <div className="filters">
        <input
          className="input"
          placeholder="Rechercher (hostname, IP)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Tous les statuts</option>
          <option value="active">Actives</option>
          <option value="disconnected">Déconnectées</option>
        </select>
      </div>

      <div className="panel">
        {data && data.items.length > 0 ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Hostname</th>
                  <th>IP</th>
                  <th>OS</th>
                  <th>CPU</th>
                  <th>RAM</th>
                  <th>Latence</th>
                  <th>Statut</th>
                  <th>Rôle</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <Link to={`/machines/${m.id}`}>
                        <strong>{m.hostname}</strong>
                      </Link>
                    </td>
                    <td>{m.ip}</td>
                    <td>{m.os_name || '—'}</td>
                    <td>{m.cpu_cores ?? '—'} cores</td>
                    <td>{m.ram_usage_percent ? `${Math.round(m.ram_usage_percent)}%` : '—'}</td>
                    <td>{m.latency_ms != null ? `${m.latency_ms.toFixed(1)} ms` : '—'}</td>
                    <td>
                      <span className={`status-dot ${m.status === 'active' ? 'active' : 'inactive'}`} />
                      {m.status}
                    </td>
                    <td>{m.role || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty message="Aucune machine" />
        )}
      </div>
    </Layout>
  )
}