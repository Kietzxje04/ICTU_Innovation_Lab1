import { createContext, useContext, useMemo, useState } from 'react'
import type { CaseContext, ReadinessCase } from './domain'
import { mockReadinessAdapter } from './readiness-adapter'

interface CreateCasePayload {
  context: CaseContext
  company_name: string
  owner: string
}

interface ReadinessContextValue {
  cases: ReadinessCase[]
  dataMode: 'mock'
  createCase: (payload: CreateCasePayload) => ReadinessCase
}

const ReadinessContext = createContext<ReadinessContextValue | null>(null)

export function ReadinessProvider({ children }: { children: React.ReactNode }) {
  const [cases, setCases] = useState<ReadinessCase[]>(() => mockReadinessAdapter.listCases())
  const value = useMemo<ReadinessContextValue>(() => ({
    cases,
    dataMode: 'mock',
    createCase: ({ context, company_name, owner }) => {
      const nextCase = mockReadinessAdapter.createCase({ context, company_name, owner })
      setCases((current) => [nextCase, ...current])
      return nextCase
    },
  }), [cases])
  return <ReadinessContext.Provider value={value}>{children}</ReadinessContext.Provider>
}

export function useReadiness() {
  const context = useContext(ReadinessContext)
  if (!context) throw new Error('useReadiness must be used inside ReadinessProvider')
  return context
}
