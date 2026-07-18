import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { readinessApi, type AuthUser } from './api'

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isCheckingSession: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)
const USER_KEY = 'nexusops-auth-user'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isCheckingSession, setIsCheckingSession] = useState(true)
  const [user, setUser] = useState<AuthUser | null>(() => {
    const stored = window.sessionStorage.getItem(USER_KEY)
    return stored ? JSON.parse(stored) as AuthUser : null
  })
  const clearSession = () => {
    setUser(null)
    window.sessionStorage.removeItem(USER_KEY)
  }
  useEffect(() => {
    // Xóa thông tin xác thực kiểu cũ: phiên hợp lệ chỉ được xác định bởi
    // cookie HttpOnly và bản ghi auth_sessions ở phía máy chủ.
    window.sessionStorage.removeItem('nexusops-access-token')
    setIsCheckingSession(true)
    readinessApi.me()
      .then((currentUser) => {
        setUser(currentUser)
        window.sessionStorage.setItem(USER_KEY, JSON.stringify(currentUser))
      })
      .catch(clearSession)
      .finally(() => setIsCheckingSession(false))
  }, [])
  const value = useMemo<AuthContextValue>(() => ({
    user,
    isAuthenticated: Boolean(user),
    isCheckingSession,
    login: async (username, password) => {
      const result = await readinessApi.login(username, password)
      window.sessionStorage.setItem(USER_KEY, JSON.stringify(result.user))
      setUser(result.user)
    },
    logout: async () => { await readinessApi.logout().catch(() => undefined); clearSession() },
  }), [user, isCheckingSession])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
