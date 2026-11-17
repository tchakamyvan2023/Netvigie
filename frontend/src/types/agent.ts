export interface AgentNetvigie {
  id: number
  name: string
  status: string
  last_heartbeat: string | null
  events_processed: number
  errors_count: number
  avg_processing_ms: number
  last_error: string | null
}

export interface AgentWazuh {
  id: number
  wazuh_id: string
  name: string
  ip: string
  status: string
  version: string | null
  os_name: string | null
  last_seen: string | null
}