import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { CaseContext, ReadinessCase, WorkflowState } from './domain'
import { apiReadinessAdapter } from './readiness-adapter'

interface CreateCasePayload {
  context: CaseContext
  company_name: string
  owner: string
}

interface ReadinessContextValue {
  cases: ReadinessCase[]
  dataMode: 'api' | 'error'
  isLoading: boolean
  error: string | null
  refresh: () => void
  createCase: (payload: CreateCasePayload) => Promise<ReadinessCase>
  rerunCase: (caseId: string, onNodeResult?: (state: WorkflowState, node: string, index: number) => void | Promise<void>) => Promise<ReadinessCase>
}

const ReadinessContext = createContext<ReadinessContextValue | null>(null)

export function ReadinessProvider({ children }: { children: React.ReactNode }) {
  const [cases, setCases] = useState<ReadinessCase[]>([])
  const [dataMode, setDataMode] = useState<'api' | 'error'>('api')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshToken, setRefreshToken] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setIsLoading(true)
    setError(null)
    apiReadinessAdapter.listCases(controller.signal)
      .then((items) => {
        setCases(items)
        setDataMode('api')
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setCases([])
        setDataMode('error')
        setError(reason instanceof Error ? reason.message : 'Không thể kết nối backend')
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })
    return () => controller.abort()
  }, [refreshToken])

  const refresh = useCallback(() => setRefreshToken((value) => value + 1), [])
  const value = useMemo<ReadinessContextValue>(() => ({
    cases,
    dataMode,
    isLoading,
    error,
    refresh,
    createCase: async ({ context, company_name, owner }) => {
      const nextCase = await apiReadinessAdapter.createCase({ context, company_name, owner })
      setCases((current) => [nextCase, ...current])
      setDataMode('api')
      return nextCase
    },
    rerunCase: async (caseId, onNodeResult) => {
      const nextCase = await apiReadinessAdapter.rerunCase(caseId, onNodeResult)
      setCases((current) => current.map((item) => item.id === caseId ? nextCase : item))
      setDataMode('api')
      return nextCase
    },
  }), [cases, dataMode, error, isLoading, refresh])
  return <ReadinessContext.Provider value={value}>{children}</ReadinessContext.Provider>
}

export function useReadiness() {
  const context = useContext(ReadinessContext)
  if (!context) throw new Error('useReadiness must be used inside ReadinessProvider')
  return context
}
