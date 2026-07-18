export type ProductType = 'CORPORATE_OVERDRAFT' | 'WORKING_CAPITAL'
export type ArtifactStatus = 'PASS' | 'WARNING' | 'BLOCKED' | 'REVIEW_REQUIRED'
export type CriticVerdict = 'PENDING' | 'PASS' | 'REVISE' | 'ESCALATE'
export type FinalStatus = 'IN_PROGRESS' | 'READY_FOR_HUMAN_REVIEW' | 'NEEDS_MORE_EVIDENCE' | 'BLOCKED'
export type CitationValidationStatus =
  | 'VALID'
  | 'WARNING_DEMO_ONLY'
  | 'REVIEW_REQUIRED'
  | 'STALE_OR_UNVERIFIED'
  | 'INVALID_QUOTE'
  | 'INVALID_HASH'
  | 'INVALID_AUTHORITY'
  | 'ABSTAIN_NO_EVIDENCE'

export interface CaseContext {
  case_id: string
  customer_id: string
  existing_customer: boolean
  product: ProductType
  requested_amount: number
  relationship_months: number
  submitted_documents: string[]
  required_documents: string[]
  annual_revenue: number | null
  pretax_profit_last_2_years: number[]
  tax_declared_revenue: number | null
  current_assets?: number | null
  current_liabilities?: number | null
  total_debt?: number | null
  total_assets?: number | null
  operating_cash_flow?: number | null
  annual_debt_service?: number | null
  collateral_ratio?: number | null
  twelve_month_account_turnover?: number | null
  account_history_months?: number | null
  twelve_month_credit_turnover?: number | null
  average_monthly_credit_inflow?: number | null
  turnover_stability_ratio?: number | null
  expected_utilization_ratio?: number | null
  negative_balance_days?: number | null
  cleanup_days?: number | null
  overdraft_purpose?: string | null
  loan_purpose?: string | null
  account_conduct_flags?: string[]
  cic_bad_debt: boolean | null
  kyc_aml_flags: string[]
  metadata: Record<string, string>
}

export interface CitationClaim {
  claim_id: string
  chunk_id: string
  quote: string
  claim_type: string
}

export interface ValidationResult {
  status: CitationValidationStatus
  reasons: string[]
}

export interface AgentArtifact {
  agent_id: string
  engine: string
  status: ArtifactStatus
  summary: string
  claims: CitationClaim[]
  metrics: Record<string, number>
  warnings: string[]
  proposed_actions: string[]
  raw: Record<string, unknown>
}

export interface TraceEvent {
  node: string
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'SKIPPED'
  started_at?: string
  duration_ms?: number
  message: string
}

export interface WorkflowState {
  case: CaseContext
  route: string[]
  artifacts: Record<string, AgentArtifact>
  citation_results: Record<string, ValidationResult>
  critic_verdict: CriticVerdict
  final_status: FinalStatus
  trace: TraceEvent[]
}

export interface EvidenceItem {
  chunk_id: string
  document_id: string
  document_number: string
  document_title: string
  domain: 'CASE_DATA' | 'AML' | 'LENDING' | 'DEMO_POLICY' | 'QUARANTINE'
  source_type: 'CASE_RECORD' | 'INTERNAL_POLICY' | 'REGULATION' | 'DEMO_CONTENT'
  source_authority: string
  validity_status: string
  effective_date: string
  article?: string
  clause?: string
  page_or_part?: string
  citation_text: string
  full_content: string
  evaluation_basis: string
  content_hash: string
  quality_status: 'ACCEPTED' | 'REVIEW_REQUIRED' | 'DEMO_ONLY' | 'REJECTED'
  validation: CitationValidationStatus
  reasons: string[]
  related_nodes: string[]
  case_field_refs: string[]
  provenance: Record<string, string>
}

export interface ReadinessCase {
  id: string
  company_name: string
  owner: string
  submitted_at: string
  sla_due: string
  sla_target?: string | null
  execution_duration_ms?: number | null
  context: CaseContext
  workflow: WorkflowState
  evidence: EvidenceItem[]
}

export const PRODUCT_LABELS: Record<ProductType, string> = {
  CORPORATE_OVERDRAFT: 'Thấu chi doanh nghiệp',
  WORKING_CAPITAL: 'Vốn lưu động',
}

export const FINAL_STATUS_LABELS: Record<FinalStatus, string> = {
  IN_PROGRESS: 'Đang phân tích',
  READY_FOR_HUMAN_REVIEW: 'Sẵn sàng rà soát',
  NEEDS_MORE_EVIDENCE: 'Cần thêm bằng chứng',
  BLOCKED: 'Bị chặn',
}

export const NODE_LABELS: Record<string, string> = {
  DOCUMENT_CLASSIFIER: 'Phân loại tài liệu',
  REQUIREMENT_MATRIX: 'Ma trận hồ sơ sản phẩm',
  OVERDRAFT_METRICS: 'Chỉ số vận hành thấu chi',
  CIC_KYC_TOOLS: 'Đối chiếu CIC và KYC',
  EXISTING_CUSTOMER_GATE: 'Kiểm tra khách hàng hiện hữu',
  PRODUCT_AGENT: 'Agent sản phẩm',
  DOCUMENT_COMPLETENESS: 'Độ đầy đủ tài liệu',
  ACCOUNT_TURNOVER: 'Phân tích vòng quay tài khoản',
  FINANCIAL_METRICS: 'Chỉ số tài chính',
  TAX_CONSISTENCY: 'Đối chiếu thuế',
  CREDIT_AGENT: 'Agent tín dụng',
  COMPLIANCE_AGENT: 'Agent tuân thủ',
  READINESS_RULE_ENGINE: 'Readiness rule engine',
  MANDATORY_CRITIC: 'Mandatory Critic',
  CITATION_VALIDATOR: 'Citation Validator',
  POLICY_GATE: 'Policy Gate',
}

export function buildRoute(context: CaseContext) {
  const route = ['EXISTING_CUSTOMER_GATE', 'PRODUCT_AGENT', 'DOCUMENT_CLASSIFIER', 'REQUIREMENT_MATRIX', 'DOCUMENT_COMPLETENESS']
  if (context.product === 'CORPORATE_OVERDRAFT') route.push('ACCOUNT_TURNOVER', 'OVERDRAFT_METRICS', 'FINANCIAL_METRICS', 'TAX_CONSISTENCY', 'CIC_KYC_TOOLS', 'CREDIT_AGENT')
  else route.push('FINANCIAL_METRICS', 'TAX_CONSISTENCY', 'CIC_KYC_TOOLS', 'CREDIT_AGENT')
  if (context.kyc_aml_flags.length) route.push('COMPLIANCE_AGENT')
  route.push('MANDATORY_CRITIC', 'CITATION_VALIDATOR', 'READINESS_RULE_ENGINE', 'POLICY_GATE')
  return route
}

export function getRouteReasons(context: CaseContext) {
  const reasons: string[] = []
  if (context.required_documents.some((item) => !context.submitted_documents.includes(item))) reasons.push('MISSING_DOCUMENTS')
  if (context.annual_revenue && context.tax_declared_revenue !== null) {
    const gap = Math.abs(context.annual_revenue - context.tax_declared_revenue) / context.annual_revenue
    if (gap > 0.1) reasons.push('FINANCIAL_TAX_MISMATCH')
  }
  if (context.kyc_aml_flags.length) reasons.push('KYC_AML_TRIGGER')
  if (context.cic_bad_debt) reasons.push('CIC_BAD_DEBT')
  if ((context.pretax_profit_last_2_years.at(-1) ?? 0) < 0) reasons.push('NEGATIVE_PRETAX_PROFIT')
  if (context.metadata.turnover_alert === 'true') reasons.push('LOW_ACCOUNT_TURNOVER')
  return reasons
}
