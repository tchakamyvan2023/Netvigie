export interface Alert {
  id: number
  wazuh_alert_id: string
  alert_ts: string
  rule_id: string | null
  rule_level: number
  rule_description: string | null
  agent_id: string | null
  agent_name: string | null
  src_ip: string | null
  dst_ip: string | null
  user: string | null
  mitre_ids: string | null
  severity: string
}