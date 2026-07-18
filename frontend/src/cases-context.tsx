import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { caseApi } from './api'
import { companies as fallbackCompanies, type Company } from './data'

interface CasesContextValue {
  companies: Company[]
  isLoading: boolean
  isUsingFallback: boolean
  refresh: () => void
}

const CasesContext = createContext<CasesContextValue | null>(null)

export function CasesProvider({ children }: { children: React.ReactNode }) {
  const [companies, setCompanies] = useState<Company[]>(fallbackCompanies)
  const [isLoading, setIsLoading] = useState(true)
  const [isUsingFallback, setIsUsingFallback] = useState(false)
  const [refreshToken, setRefreshToken] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setIsLoading(true)

    caseApi.list(controller.signal)
      .then((items) => {
        const hasBackendData = items.length > 0
        setCompanies(hasBackendData ? items : fallbackCompanies)
        setIsUsingFallback(!hasBackendData)
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setCompanies(fallbackCompanies)
        setIsUsingFallback(true)
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [refreshToken])

  const value = useMemo<CasesContextValue>(() => ({
    companies,
    isLoading,
    isUsingFallback,
    refresh: () => setRefreshToken((value) => value + 1),
  }), [companies, isLoading, isUsingFallback])

  return <CasesContext.Provider value={value}>{children}</CasesContext.Provider>
}

export function useCases() {
  const context = useContext(CasesContext)
  if (!context) throw new Error('useCases must be used inside CasesProvider')
  return context
}
