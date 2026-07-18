import { createContext, useContext, useMemo, useState } from 'react'
import { readinessApi, type AuthUser } from './api'

interface AuthContextValue {
  token: string | null
  user: AuthUser | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)
const TOKEN_KEY = 'nexusops-access-token'
const USER_KEY = 'nexusops-auth-user'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState(() => window.localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<AuthUser | null>(() => {
    const stored = window.localStorage.getItem(USER_KEY)
    return stored ? JSON.parse(stored) as AuthUser : null
  })
  const value = useMemo<AuthContextValue>(() => ({
    token,
    user,
    isAuthenticated: Boolean(token && user),
    login: async (username, password) => {
      const result = await readinessApi.login(username, password)
      setToken(result.access_token); setUser(result.user)
      window.localStorage.setItem(TOKEN_KEY, result.access_token)
      window.localStorage.setItem(USER_KEY, JSON.stringify(result.user))
    },
    logout: () => {
      setToken(null); setUser(null)
      window.localStorage.removeItem(TOKEN_KEY); window.localStorage.removeItem(USER_KEY)
    },
  }), [token, user])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}

export function authToken() {
  return window.localStorage.getItem(TOKEN_KEY)
}
