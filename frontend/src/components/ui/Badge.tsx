export function Badge({ severity, children }: { severity?: string; children: React.ReactNode }) {
  const cls = severity || 'neutral'
  return <span className={`badge ${cls}`}>{children}</span>
}