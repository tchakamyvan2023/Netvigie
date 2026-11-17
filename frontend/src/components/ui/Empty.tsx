export function Empty({ message = 'Aucune donnée' }: { message?: string }) {
  return <div className="empty">{message}</div>
}