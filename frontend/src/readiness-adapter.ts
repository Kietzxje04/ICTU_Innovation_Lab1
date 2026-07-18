import type { CaseContext, ReadinessCase, WorkflowState } from './domain'
import { readinessApi } from './api'

export interface ReadinessAdapter {
  listCases(signal?: AbortSignal): Promise<ReadinessCase[]>
  createCase(payload: { context: CaseContext; company_name: string; owner: string }): Promise<ReadinessCase>
  rerunCase(caseId: string, onNodeResult?: (state: WorkflowState, node: string, index: number) => void | Promise<void>): Promise<ReadinessCase>
}

export const apiReadinessAdapter: ReadinessAdapter = {
  listCases(signal) {
    return readinessApi.list(signal)
  },
  createCase(payload) {
    return readinessApi.create(payload)
  },
  rerunCase(caseId, onNodeResult) {
    return readinessApi.rerun(caseId, onNodeResult)
  },
}
