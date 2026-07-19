import type { CaseContext, ReadinessCase, WorkflowState } from './domain'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

interface ApiResponse<T> {
  data: T
  meta?: Record<string, unknown> | null
  error?: { code?: string; message?: string; details?: unknown } | null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...init?.headers,
    },
  })
  const payload = (await response.json()) as ApiResponse<T>
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('nexusops:unauthorized'))
    throw new Error(payload.error?.message ?? `Backend request failed: ${response.status}`)
  }
  return payload.data
}

export interface CreateReadinessCasePayload {
  context: CaseContext
  company_name: string
  owner: string
}

export interface AuthUser {
  user_id: string
  username: string
  full_name: string
  email: string
  role_id: string
  role_name?: string
  approval_limit?: number | null
  permissions?: string[]
}

export interface ProductIntakeSchema {
  product: CaseContext['product']
  required_documents: string[]
  fields: Array<{ name: string; type: string; required: boolean }>
  rules: Array<Record<string, unknown>>
  synthetic: boolean
}

export interface RoutePreview {
  product: CaseContext['product']
  required_documents: string[]
  route: string[]
  hardness: number
  reasons: string[]
}

export interface LoanApprovalStatus {
  case_id: string
  amount: number
  status: 'PENDING' | 'TRANSFERRED' | 'APPROVED'
  current_role: string
  required_role: string
  assigned_to: string | null
  ready: boolean
  blockers: string[]
  can_approve: boolean
  can_transfer: boolean
  must_transfer: boolean
  permissions: string[]
  approved_by_name?: string | null
  approved_at?: string | null
}

export interface LoanApprovalRecord {
  approval_id: string
  case_id: string
  status: string
  current_role: string
  assigned_to: string | null
  approved_by: string | null
  decision_reason: string | null
  history: Array<Record<string, unknown>>
}

interface StepwiseRunResponse {
  run_id: string
  state: WorkflowState
  node?: string
  run_status?: string
}

export const readinessApi = {
  login: async (username: string, password: string) => request<{ expires_at: string; user: AuthUser }>('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }),
  }),
  me: () => request<AuthUser>('/api/auth/me'),
  logout: () => request<{ logged_out: boolean }>('/api/auth/logout', { method: 'POST' }),
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
  rerun: async (caseId: string, onNodeResult?: (state: WorkflowState, node: string, index: number) => void | Promise<void>) => {
    let run = await request<StepwiseRunResponse>(`/api/cases/${encodeURIComponent(caseId)}/workflow-runs`, { method: 'POST' })
    for (let index = 0; index < run.state.route.length; index += 1) {
      const node = run.state.route[index]
      run = await request<StepwiseRunResponse>(`/api/cases/${encodeURIComponent(caseId)}/workflow-runs/${encodeURIComponent(run.run_id)}/nodes/${encodeURIComponent(node)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: run.state }),
      })
      await onNodeResult?.(run.state, node, index)
    }
    return request<ReadinessCase>(`/api/readiness/cases/${encodeURIComponent(caseId)}`)
  },
  productSchema: (product: CaseContext['product'], signal?: AbortSignal) =>
    request<ProductIntakeSchema>(`/api/v3/products/${product}/intake-schema`, { signal }),
  previewRoute: (context: CaseContext, signal?: AbortSignal) =>
    request<RoutePreview>('/api/v3/cases/preview-route', {
      method: 'POST',
      signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ context }),
    }),
  loanApproval: (caseId: string, signal?: AbortSignal) =>
    request<LoanApprovalStatus>(`/api/cases/${encodeURIComponent(caseId)}/loan-approval`, { signal }),
  approveLoan: (caseId: string, reason?: string) =>
    request<LoanApprovalRecord>(`/api/cases/${encodeURIComponent(caseId)}/loan-approval/approve`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason: reason || null }),
    }),
  transferLoan: (caseId: string, reason: string) =>
    request<LoanApprovalRecord>(`/api/cases/${encodeURIComponent(caseId)}/loan-approval/transfer`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason }),
    }),
}
