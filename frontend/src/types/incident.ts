export interface Incident {
  id: number
  incident_id: string
  incident_ts: string
  verdict: string
  severity: string
  confidence: number
  status: string
  title: string
  description: string | null
  primary_machine_id: number | null
  evidence_json: Record<string, unknown> | null
  recommendation: string | null
  proposed_action: string | null
  action_target: string | null
  assigned_to: string | null
  closed_at: string | null
}