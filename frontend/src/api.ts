import type { Company } from './data'
import type { CaseContext, ReadinessCase } from './domain'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

interface ApiResponse<T> {
  data: T
  meta?: Record<string, unknown> | null
}

export interface ProposedAction {
  id: string
  case_id: string
  type: string
  payload: Record<string, unknown>
  payload_hash: string
  status: 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'SUCCEEDED'
  created_by: string
  approved_by?: string | null
  decided_at?: string | null
}

export interface ResolutionPackage {
  case: Company
  primary_outcome: string
  blockers: string[]
  routes: string[]
  reason_codes: string[]
  eligible_actions: string[]
  proposed_action: ProposedAction
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...init?.headers,
    },
  })

  const payload = (await response.json()) as ApiResponse<T>
  if (!response.ok) {
    const errorPayload = payload as ApiResponse<T> & { error?: { message?: string } | null }
    throw new Error(errorPayload.error?.message ?? `Backend request failed: ${response.status}`)
  }
  return payload.data
}

export interface CreateReadinessCasePayload {
  context: CaseContext
  company_name: string
  owner: string
}

export const readinessApi = {
  list: (signal?: AbortSignal) => request<ReadinessCase[]>('/api/readiness/cases', { signal }),
  get: (caseId: string, signal?: AbortSignal) =>
    request<ReadinessCase>(`/api/readiness/cases/${encodeURIComponent(caseId)}`, { signal }),
  create: (payload: CreateReadinessCasePayload) =>
    request<ReadinessCase>('/api/readiness/cases', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': `create-${payload.context.case_id}`,
      },
      body: JSON.stringify(payload),
    }),
}

export const caseApi = {
  list: (signal?: AbortSignal) => request<Company[]>('/api/cases', { signal }),
  get: (caseId: string, signal?: AbortSignal) =>
    request<Company>(`/api/cases/${encodeURIComponent(caseId)}`, { signal }),
}

const demoApprovalHeaders = {
  'Content-Type': 'application/json',
  'X-User-Id': 'frontend-demo-approver',
  'X-Role': 'approver',
}

export const resolutionApi = {
  get: (caseId: string, signal?: AbortSignal) =>
    request<ResolutionPackage>(`/api/cases/${encodeURIComponent(caseId)}/resolution-package`, { signal }),
}

export const actionApi = {
  list: (caseId: string, signal?: AbortSignal) =>
    request<ProposedAction[]>(`/api/cases/${encodeURIComponent(caseId)}/actions`, { signal }),
  approve: (caseId: string, action: ProposedAction) =>
    request<ProposedAction>(`/api/cases/${encodeURIComponent(caseId)}/actions/${encodeURIComponent(action.id)}/approve`, {
      method: 'POST',
      headers: {
        ...demoApprovalHeaders,
        'Idempotency-Key': `approve-${action.id}-${action.payload_hash}`,
      },
      body: JSON.stringify({ approved_payload_hash: action.payload_hash }),
    }),
  reject: (caseId: string, action: ProposedAction) =>
    request<ProposedAction>(`/api/cases/${encodeURIComponent(caseId)}/actions/${encodeURIComponent(action.id)}/reject`, {
      method: 'POST',
      headers: demoApprovalHeaders,
      body: JSON.stringify({ reason: 'Chuyển cấp để chuyên viên rà soát' }),
    }),
}
