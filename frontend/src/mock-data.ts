import {
  buildRoute,
  getRouteReasons,
  type AgentArtifact,
  type CaseContext,
  type EvidenceItem,
  type FinalStatus,
  type ReadinessCase,
} from './domain'

const REQUIRED_OVERDRAFT = ['BUSINESS_REGISTRATION', 'BANK_STATEMENTS_12M', 'CIC_REPORT', 'LOAN_PURPOSE_PLAN']
const REQUIRED_WORKING_CAPITAL = ['BUSINESS_REGISTRATION', 'FINANCIAL_STATEMENTS_2Y', 'TAX_RETURNS_2Y', 'CIC_REPORT', 'WORKING_CAPITAL_PLAN']

const artifact = (
  agent_id: string,
  status: AgentArtifact['status'],
  summary: string,
  options: Partial<AgentArtifact> = {},
): AgentArtifact => ({
  agent_id,
  engine: agent_id.includes('AGENT') ? 'DETERMINISTIC_PLUS_LLM' : 'DETERMINISTIC',
  status,
  summary,
  claims: [],
  metrics: {},
  warnings: [],
  proposed_actions: [],
  raw: {},
  ...options,
})

function buildArtifacts(context: CaseContext) {
  const missing = context.required_documents.filter((item) => !context.submitted_documents.includes(item))
  const taxGap = context.annual_revenue && context.tax_declared_revenue !== null
    ? Math.abs(context.annual_revenue - context.tax_declared_revenue) / context.annual_revenue
    : null
  const blocked = !context.existing_customer || Boolean(context.cic_bad_debt)
  const review = missing.length > 0 || Boolean(taxGap && taxGap > 0.1) || context.kyc_aml_flags.length > 0
  const artifacts: Record<string, AgentArtifact> = {
    EXISTING_CUSTOMER_GATE: artifact('EXISTING_CUSTOMER_GATE', context.existing_customer ? 'PASS' : 'BLOCKED', context.existing_customer ? 'Khách hàng hiện hữu đã được xác nhận.' : 'Khách hàng mới nằm ngoài phạm vi demo.'),
    PRODUCT_AGENT: artifact('PRODUCT_AGENT', 'PASS', `Đã chọn workflow ${context.product}.`),
    DOCUMENT_COMPLETENESS: artifact('DOCUMENT_COMPLETENESS', missing.length ? 'REVIEW_REQUIRED' : 'PASS', missing.length ? `Thiếu ${missing.length} tài liệu bắt buộc.` : 'Bộ tài liệu đầu vào đã đầy đủ.', {
      metrics: { completeness_ratio: context.required_documents.length ? (context.required_documents.length - missing.length) / context.required_documents.length : 1 },
      warnings: missing,
      proposed_actions: missing.length ? ['REQUEST_MISSING_DOCUMENTS'] : [],
    }),
    CREDIT_AGENT: artifact('CREDIT_AGENT', context.cic_bad_debt ? 'BLOCKED' : review ? 'REVIEW_REQUIRED' : 'PASS', context.cic_bad_debt ? 'Phát hiện lịch sử nợ xấu CIC, cần chuyên viên xử lý.' : 'Chỉ số tín dụng đã được tổng hợp để cán bộ rà soát.', {
      warnings: context.cic_bad_debt ? ['CIC_BAD_DEBT'] : [],
      proposed_actions: context.cic_bad_debt ? ['ESCALATE_TO_CREDIT_SPECIALIST'] : [],
    }),
    READINESS_RULE_ENGINE: artifact('READINESS_RULE_ENGINE', blocked ? 'BLOCKED' : review ? 'REVIEW_REQUIRED' : 'PASS', blocked ? 'Hồ sơ có điều kiện chặn.' : review ? 'Hồ sơ cần bổ sung hoặc xác minh.' : 'Các điều kiện readiness đã đạt.'),
    MANDATORY_CRITIC: artifact('MANDATORY_CRITIC', blocked || review ? 'REVIEW_REQUIRED' : 'PASS', blocked || review ? 'Critic yêu cầu xử lý các điểm chưa giải quyết trước HITL.' : 'Critic không phát hiện mâu thuẫn trọng yếu.', {
      warnings: getRouteReasons(context).map((reason) => `UNRESOLVED:${reason}`),
    }),
    CITATION_VALIDATOR: artifact('CITATION_VALIDATOR', 'PASS', 'Các trích dẫn hiển thị đã qua kiểm tra quote, hash và authority.'),
    POLICY_GATE: artifact('POLICY_GATE', blocked ? 'BLOCKED' : review ? 'REVIEW_REQUIRED' : 'PASS', blocked ? 'Policy gate chặn chuyển bước.' : 'Hồ sơ đủ điều kiện chuyển cán bộ rà soát.'),
  }

  if (context.product === 'CORPORATE_OVERDRAFT') {
    artifacts.ACCOUNT_TURNOVER = artifact('ACCOUNT_TURNOVER', 'PASS', 'Dòng tiền tài khoản được đánh giá ổn định.', { metrics: { average_monthly_turnover: 8_450_000_000 } })
  } else {
    artifacts.FINANCIAL_METRICS = artifact('FINANCIAL_METRICS', taxGap && taxGap > 0.1 ? 'WARNING' : 'PASS', 'Đã tính doanh thu và xu hướng lợi nhuận hai năm.', { metrics: { annual_revenue: context.annual_revenue ?? 0, latest_pretax_profit: context.pretax_profit_last_2_years.at(-1) ?? 0 } })
    artifacts.TAX_CONSISTENCY = artifact('TAX_CONSISTENCY', taxGap && taxGap > 0.1 ? 'REVIEW_REQUIRED' : 'PASS', taxGap && taxGap > 0.1 ? `Chênh lệch doanh thu và khai thuế ${(taxGap * 100).toFixed(1)}%.` : 'Doanh thu tài chính và khai thuế nhất quán.', {
      metrics: { tax_gap_ratio: taxGap ?? 0 },
      warnings: taxGap && taxGap > 0.1 ? ['FINANCIAL_TAX_MISMATCH'] : [],
      proposed_actions: taxGap && taxGap > 0.1 ? ['REQUEST_TAX_RECONCILIATION'] : [],
    })
  }
  if (context.kyc_aml_flags.length) {
    artifacts.COMPLIANCE_AGENT = artifact('COMPLIANCE_AGENT', 'REVIEW_REQUIRED', 'AML route được kích hoạt và cần cán bộ tuân thủ xác minh.', {
      engine: 'RULES_PLUS_RAG', warnings: context.kyc_aml_flags, proposed_actions: ['ESCALATE_TO_COMPLIANCE'],
    })
  }
  return artifacts
}

function evidenceFor(context: CaseContext): EvidenceItem[] {
  return [
    {
      chunk_id: `${context.case_id}-LENDING-01`, document_id: 'SME-POLICY-V31', document_number: 'POL-SME-3.1',
      document_title: 'SME Lending Readiness Policy', domain: 'LENDING', source_authority: 'Internal Policy Owner',
      validity_status: 'EFFECTIVE', citation_text: 'Hồ sơ readiness phải được chuyển cán bộ rà soát khi còn thiếu tài liệu bắt buộc hoặc có sai lệch dữ liệu trọng yếu.',
      content_hash: 'sha256:8cf0d2b7e6', quality_status: 'ACCEPTED', validation: 'VALID', reasons: [],
    },
    {
      chunk_id: `${context.case_id}-DEMO-02`, document_id: 'DEMO-GUIDE', document_number: 'DEMO-2026',
      document_title: 'Demo policy — Human in the loop', domain: 'DEMO_POLICY', source_authority: 'Demo Content',
      validity_status: 'DEMO_ONLY', citation_text: 'Hệ thống chỉ đề xuất bước xử lý tiếp theo và không tự động phê duyệt hoặc từ chối khoản vay.',
      content_hash: 'sha256:3ac1d73e11', quality_status: 'DEMO_ONLY', validation: 'WARNING_DEMO_ONLY', reasons: ['Nguồn chỉ dùng cho môi trường demo.'],
    },
  ]
}

export function makeReadinessCase(
  context: CaseContext,
  company_name: string,
  owner: string,
  submitted_at = new Date().toISOString(),
): ReadinessCase {
  const reasons = getRouteReasons(context)
  const blocked = !context.existing_customer || Boolean(context.cic_bad_debt)
  const final_status: FinalStatus = blocked ? 'BLOCKED' : reasons.length ? 'NEEDS_MORE_EVIDENCE' : 'READY_FOR_HUMAN_REVIEW'
  const route = buildRoute(context)
  const evidence = evidenceFor(context)
  return {
    id: context.case_id,
    company_name,
    owner,
    submitted_at,
    sla_due: blocked ? 'Tạm dừng' : reasons.length ? '02:15:00' : '00:45:00',
    context,
    evidence,
    workflow: {
      case: context,
      route,
      artifacts: buildArtifacts(context),
      citation_results: Object.fromEntries(evidence.map((item) => [item.chunk_id, { status: item.validation, reasons: item.reasons }])),
      critic_verdict: blocked ? 'ESCALATE' : reasons.length ? 'REVISE' : 'PASS',
      final_status,
      trace: route.map((node, index) => ({ node, status: 'COMPLETED', started_at: new Date(Date.now() - (route.length - index) * 1200).toISOString(), duration_ms: 320 + index * 47, message: `${node} hoàn tất.` })),
    },
  }
}

export const mockCases: ReadinessCase[] = [
  makeReadinessCase({
    case_id: 'CASE-WC-2026-0142', customer_id: 'CUS-001842', existing_customer: true, product: 'WORKING_CAPITAL', requested_amount: 12_000_000_000,
    relationship_months: 38, submitted_documents: ['BUSINESS_REGISTRATION', 'FINANCIAL_STATEMENTS_2Y', 'CIC_REPORT', 'WORKING_CAPITAL_PLAN'], required_documents: REQUIRED_WORKING_CAPITAL,
    annual_revenue: 48_000_000_000, pretax_profit_last_2_years: [3_200_000_000, 3_850_000_000], tax_declared_revenue: 39_500_000_000,
    cic_bad_debt: false, kyc_aml_flags: [], metadata: { industry: 'Phân phối thiết bị', branch: 'ICTU Thái Nguyên', currency: 'VND' },
  }, 'Công ty TNHH Công nghệ Toàn Cầu', 'Nguyễn Minh Anh', '2026-07-18T03:45:00.000Z'),
  makeReadinessCase({
    case_id: 'CASE-OD-2026-0138', customer_id: 'CUS-001227', existing_customer: true, product: 'CORPORATE_OVERDRAFT', requested_amount: 5_500_000_000,
    relationship_months: 64, submitted_documents: REQUIRED_OVERDRAFT, required_documents: REQUIRED_OVERDRAFT,
    annual_revenue: 76_000_000_000, pretax_profit_last_2_years: [5_400_000_000, 6_100_000_000], tax_declared_revenue: 74_800_000_000,
    cic_bad_debt: false, kyc_aml_flags: [], metadata: { industry: 'Sản xuất bao bì', branch: 'ICTU Hà Nội', currency: 'VND' },
  }, 'Công ty Cổ phần Bao bì Hưng Phát', 'Trần Hoàng Nam', '2026-07-18T02:10:00.000Z'),
  makeReadinessCase({
    case_id: 'CASE-WC-2026-0129', customer_id: 'CUS-004105', existing_customer: true, product: 'WORKING_CAPITAL', requested_amount: 18_000_000_000,
    relationship_months: 19, submitted_documents: REQUIRED_WORKING_CAPITAL, required_documents: REQUIRED_WORKING_CAPITAL,
    annual_revenue: 91_000_000_000, pretax_profit_last_2_years: [2_100_000_000, 1_650_000_000], tax_declared_revenue: 90_500_000_000,
    cic_bad_debt: false, kyc_aml_flags: ['BENEFICIAL_OWNER_REVIEW'], metadata: { industry: 'Xuất nhập khẩu', branch: 'ICTU Bắc Ninh', currency: 'VND' },
  }, 'Công ty Cổ phần Xuất nhập khẩu Đông Á', 'Lê Thu Hà', '2026-07-17T09:20:00.000Z'),
  makeReadinessCase({
    case_id: 'CASE-OD-2026-0117', customer_id: 'CUS-003014', existing_customer: true, product: 'CORPORATE_OVERDRAFT', requested_amount: 3_200_000_000,
    relationship_months: 11, submitted_documents: ['BUSINESS_REGISTRATION', 'BANK_STATEMENTS_12M', 'CIC_REPORT'], required_documents: REQUIRED_OVERDRAFT,
    annual_revenue: 22_000_000_000, pretax_profit_last_2_years: [900_000_000, 720_000_000], tax_declared_revenue: 21_700_000_000,
    cic_bad_debt: true, kyc_aml_flags: [], metadata: { industry: 'Vận tải', branch: 'ICTU Hải Phòng', currency: 'VND' },
  }, 'Công ty TNHH Vận tải Minh Long', 'Phạm Đức Long', '2026-07-17T06:05:00.000Z'),
]

export const documentOptions = {
  CORPORATE_OVERDRAFT: REQUIRED_OVERDRAFT,
  WORKING_CAPITAL: REQUIRED_WORKING_CAPITAL,
} as const

