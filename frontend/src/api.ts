import type { Company } from './data'

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

  if (!response.ok) {
    throw new Error(`Backend request failed: ${response.status}`)
  }

  const payload = (await response.json()) as ApiResponse<T>
  return payload.data
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
