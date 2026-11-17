import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { authApi, UserMe } from '@/api/auth'

interface AuthContextType {
  user: UserMe | null
  token: string | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const storedToken = localStorage.getItem('netvigie_token')
    const storedUser = localStorage.getItem('netvigie_user')
    if (storedToken && storedUser) {
      setToken(storedToken)
      setUser(JSON.parse(storedUser))
    }
    setLoading(false)
  }, [])

  const login = async (username: string, password: string) => {
    const res = await authApi.login(username, password)
    localStorage.setItem('netvigie_token', res.access_token)
    setToken(res.access_token)

    const me = await authApi.me()
    localStorage.setItem('netvigie_user', JSON.stringify(me))
    setUser(me)
  }

  const logout = () => {
    localStorage.removeItem('netvigie_token')
    localStorage.removeItem('netvigie_user')
    setToken(null)
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider
      value={{ user, token, loading, login, logout, isAuthenticated: !!token }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}