import { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function Layout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Topbar title={title} />
        {children}
      </main>
    </div>
  )
}