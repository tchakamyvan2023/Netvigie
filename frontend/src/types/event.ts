export interface Event {
  id: number
  event_id: string
  event_ts: string
  source: string
  event_type: string
  category: string | null
  severity: string
  confidence: number
  machine_id: number | null
  src_ip: string | null
  dst_ip: string | null
  user: string | null
  description: string | null
}