import type { CaseContext, ReadinessCase } from './domain'
import { makeReadinessCase, mockCases } from './mock-data'

export interface ReadinessAdapter {
  listCases(): ReadinessCase[]
  createCase(payload: { context: CaseContext; company_name: string; owner: string }): ReadinessCase
}

/** Adapter boundary: replace this implementation with the FastAPI client after backend contract freeze. */
export const mockReadinessAdapter: ReadinessAdapter = {
  listCases() {
    return mockCases
  },
  createCase({ context, company_name, owner }) {
    return makeReadinessCase(context, company_name, owner)
  },
}
