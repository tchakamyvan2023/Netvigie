export interface Machine {
  id: number
  agent_id: string | null
  hostname: string
  ip: string
  os_name: string | null
  os_version: string | null
  kernel: string | null
  cpu_name: string | null
  cpu_cores: number | null
  ram_total_mb: number | null
  ram_usage_percent: number | null
  disk_usage_percent: number | null
  latency_ms: number | null
  packet_loss_percent: number | null
  status: string
  is_excluded: boolean
  role: string | null
  criticality: string | null
  display_name: string | null
  last_seen: string | null
  last_sync: string
}