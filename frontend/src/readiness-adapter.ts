import type { CaseContext, ReadinessCase } from './domain'
import { readinessApi } from './api'

export interface ReadinessAdapter {
  listCases(signal?: AbortSignal): Promise<ReadinessCase[]>
  createCase(payload: { context: CaseContext; company_name: string; owner: string }): Promise<ReadinessCase>
}

export const apiReadinessAdapter: ReadinessAdapter = {
  listCases(signal) {
    return readinessApi.list(signal)
  },
  createCase(payload) {
    return readinessApi.create(payload)
  },
}
