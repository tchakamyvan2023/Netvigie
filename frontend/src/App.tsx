import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from '@/auth/AuthContext'
import { ProtectedRoute } from '@/auth/ProtectedRoute'
import { LoginPage } from '@/auth/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { MachinesPage } from '@/pages/MachinesPage'
import { MachineDetailPage } from '@/pages/MachineDetailPage'
import { IncidentsPage } from '@/pages/IncidentsPage'
import { LogsPage } from '@/pages/LogsPage'
import { AgentsPage } from '@/pages/AgentsPage'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/machines"
          element={
            <ProtectedRoute>
              <MachinesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/machines/:id"
          element={
            <ProtectedRoute>
              <MachineDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/incidents"
          element={
            <ProtectedRoute>
              <IncidentsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/logs"
          element={
            <ProtectedRoute>
              <LogsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/agents"
          element={
            <ProtectedRoute>
              <AgentsPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  )
}