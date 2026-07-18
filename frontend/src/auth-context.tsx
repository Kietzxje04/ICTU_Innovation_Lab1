import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { readinessApi, type AuthUser } from './api'

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isCheckingSession: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isCheckingSession, setIsCheckingSession] = useState(true)
  const [user, setUser] = useState<AuthUser | null>(null)
  const clearSession = useCallback(() => setUser(null), [])
  const verifySession = useCallback(async () => {
    setIsCheckingSession(true)
    try {
      setUser(await readinessApi.me())
    } catch {
      clearSession()
    } finally {
      setIsCheckingSession(false)
    }
  }, [clearSession])

  useEffect(() => {
    window.sessionStorage.removeItem('nexusops-access-token')
    window.sessionStorage.removeItem('nexusops-auth-user')
    void verifySession()

    const handlePageShow = () => { void verifySession() }
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') void verifySession()
    }
    const handleUnauthorized = () => {
      clearSession()
      setIsCheckingSession(false)
    }
    window.addEventListener('pageshow', handlePageShow)
    window.addEventListener('nexusops:unauthorized', handleUnauthorized)
    document.addEventListener('visibilitychange', handleVisibility)
    return () => {
      window.removeEventListener('pageshow', handlePageShow)
      window.removeEventListener('nexusops:unauthorized', handleUnauthorized)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [clearSession, verifySession])
  const value = useMemo<AuthContextValue>(() => ({
    user,
    isAuthenticated: Boolean(user),
    isCheckingSession,
    login: async (username, password) => {
      const result = await readinessApi.login(username, password)
      setUser(result.user)
    },
    logout: async () => {
      clearSession()
      await readinessApi.logout().catch(() => undefined)
    },
  }), [user, isCheckingSession, clearSession])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
