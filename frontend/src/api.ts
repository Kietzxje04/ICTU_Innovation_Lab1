import type { CaseContext, ReadinessCase } from './domain'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

interface ApiResponse<T> {
  data: T
  meta?: Record<string, unknown> | null
  error?: { code?: string; message?: string; details?: unknown } | null
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
  if (!response.ok) throw new Error(payload.error?.message ?? `Backend request failed: ${response.status}`)
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
