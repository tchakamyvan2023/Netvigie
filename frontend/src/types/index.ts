export * from './machine'
export * from './event'
export * from './alert'
export * from './incident'
export * from './agent'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface OverviewStats {
  total_machines: number
  active_machines: number
  unreachable_machines: number
  excluded_machines: number
  total_alerts: number
  alerts_last_hour: number
  critical_alerts: number
  total_incidents: number
  open_incidents: number
  incidents_by_verdict: Record<string, number>
  incidents_by_severity: Record<string, number>
  agents_status: Record<string, string>
  wazuh_status: string
}

export interface TimeSeriesPoint {
  timestamp: string
  value: number
}

export interface TimeSeriesResponse {
  series: TimeSeriesPoint[]
  metric: string
  period: string
}