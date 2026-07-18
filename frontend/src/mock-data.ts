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
  const latestProfit = context.pretax_profit_last_2_years.at(-1) ?? 0
  const lossMaking = latestProfit < 0
  const turnoverAlert = context.metadata.turnover_alert === 'true'
  const blocked = !context.existing_customer || Boolean(context.cic_bad_debt)
  const review = missing.length > 0 || Boolean(taxGap && taxGap > 0.1) || context.kyc_aml_flags.length > 0 || lossMaking || turnoverAlert
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
    artifacts.ACCOUNT_TURNOVER = artifact('ACCOUNT_TURNOVER', turnoverAlert ? 'REVIEW_REQUIRED' : 'PASS', turnoverAlert ? 'Vòng quay tài khoản thấp hơn mức kỳ vọng của sản phẩm thấu chi.' : 'Dòng tiền tài khoản được đánh giá ổn định.', {
      metrics: { average_monthly_turnover: turnoverAlert ? 1_150_000_000 : 8_450_000_000 },
      warnings: turnoverAlert ? ['LOW_ACCOUNT_TURNOVER'] : [], proposed_actions: turnoverAlert ? ['REQUEST_CASH_FLOW_EXPLANATION'] : [],
    })
  } else {
    artifacts.FINANCIAL_METRICS = artifact('FINANCIAL_METRICS', lossMaking || (taxGap && taxGap > 0.1) ? 'WARNING' : 'PASS', lossMaking ? 'Doanh nghiệp ghi nhận lỗ trước thuế ở năm gần nhất.' : 'Đã tính doanh thu và xu hướng lợi nhuận hai năm.', {
      metrics: { annual_revenue: context.annual_revenue ?? 0, latest_pretax_profit: latestProfit },
      warnings: lossMaking ? ['NEGATIVE_PRETAX_PROFIT'] : [], proposed_actions: lossMaking ? ['REQUEST_LOSS_EXPLANATION'] : [],
    })
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
      chunk_id: `${context.case_id}-CASE-00`, document_id: context.case_id, document_number: context.case_id,
      document_title: 'Hồ sơ khách hàng và dữ liệu đầu vào', domain: 'CASE_DATA', source_type: 'CASE_RECORD', source_authority: 'Hệ thống hồ sơ khách hàng',
      validity_status: 'CURRENT_SNAPSHOT', effective_date: context.metadata.snapshot_date ?? '2026-07-18', page_or_part: 'CaseContext',
      citation_text: `Hồ sơ ${context.case_id} ghi nhận ${context.submitted_documents.length}/${context.required_documents.length} tài liệu đã nộp, doanh thu ${new Intl.NumberFormat('vi-VN').format(context.annual_revenue ?? 0)} đồng và mã khách hàng ${context.customer_id}.`,
      full_content: `Bản chụp CaseContext dùng cho phiên readiness. Khách hàng hiện hữu: ${context.existing_customer ? 'Có' : 'Không'}. Sản phẩm: ${context.product}. Số tiền đề nghị: ${new Intl.NumberFormat('vi-VN').format(context.requested_amount)} đồng. Tài liệu đã nộp: ${context.submitted_documents.join(', ') || 'Chưa có'}. Tài liệu bắt buộc: ${context.required_documents.join(', ')}. Doanh thu năm: ${context.annual_revenue ?? 'Chưa cung cấp'}. Doanh thu khai thuế: ${context.tax_declared_revenue ?? 'Chưa cung cấp'}. Cờ KYC/AML: ${context.kyc_aml_flags.join(', ') || 'Không có'}. Cờ CIC: ${context.cic_bad_debt ? 'Có nợ xấu' : 'Không có nợ xấu'}.`,
      evaluation_basis: 'Dùng để đối chiếu trực tiếp các trường CaseContext với kết quả của node; đây là dữ liệu hồ sơ, không phải chính sách.',
      content_hash: 'sha256:case-context-2026', quality_status: 'ACCEPTED', validation: 'VALID', reasons: [], related_nodes: ['EXISTING_CUSTOMER_GATE', 'PRODUCT_AGENT', 'DOCUMENT_COMPLETENESS', 'FINANCIAL_METRICS', 'ACCOUNT_TURNOVER', 'CREDIT_AGENT'],
      case_field_refs: ['existing_customer', 'product', 'requested_amount', 'submitted_documents', 'required_documents', 'annual_revenue', 'tax_declared_revenue', 'cic_bad_debt'], provenance: { captured_by: 'readiness-intake', snapshot: context.metadata.snapshot_date ?? '2026-07-18' },
    },
    {
      chunk_id: `${context.case_id}-LENDING-01`, document_id: 'SME-POLICY-V31', document_number: 'POL-SME-3.1',
      document_title: 'SME Lending Readiness Policy', domain: 'LENDING', source_type: 'INTERNAL_POLICY', source_authority: 'Khối Chính sách tín dụng',
      validity_status: 'EFFECTIVE', effective_date: '2026-01-15', article: 'Điều 3', clause: '3.2', page_or_part: 'Trang 12', citation_text: 'Hồ sơ readiness phải được chuyển cán bộ rà soát khi còn thiếu tài liệu bắt buộc hoặc có sai lệch dữ liệu trọng yếu.',
      full_content: 'Điều 3.2 — Hồ sơ SME chỉ được đánh dấu sẵn sàng chuyển cán bộ rà soát sau khi hệ thống đã kiểm tra độ đầy đủ tài liệu, các sai lệch tài chính trọng yếu và các cờ tuân thủ. Readiness artifact không phải quyết định phê duyệt hoặc từ chối khoản vay.',
      evaluation_basis: 'Làm căn cứ cho Readiness Rule Engine, Mandatory Critic và Policy Gate khi xác định hồ sơ cần bổ sung bằng chứng hoặc chuyển Human-in-the-loop.', content_hash: 'sha256:8cf0d2b7e6', quality_status: 'ACCEPTED', validation: 'VALID', reasons: [], related_nodes: ['READINESS_RULE_ENGINE', 'MANDATORY_CRITIC', 'POLICY_GATE'], case_field_refs: ['submitted_documents', 'required_documents', 'kyc_aml_flags'], provenance: { version: '3.1', owner: 'credit-policy' },
    },
    {
      chunk_id: `${context.case_id}-TAX-02`, document_id: 'SME-TAX-GUIDE', document_number: 'TAX-REC-2.4',
      document_title: 'Hướng dẫn đối chiếu doanh thu và thuế', domain: 'LENDING', source_type: 'INTERNAL_POLICY', source_authority: 'Khối Quản trị rủi ro tín dụng',
      validity_status: 'EFFECTIVE', effective_date: '2025-11-01', article: 'Mục 2', clause: '2.4', page_or_part: 'Trang 8', citation_text: 'Chênh lệch doanh thu khai thuế trên 10% hoặc lợi nhuận âm phải được giải trình và chuyển cán bộ rà soát.',
      full_content: 'Mục 2.4 — Agent phải tính tỷ lệ chênh lệch giữa doanh thu tài chính và doanh thu khai thuế. Nếu chênh lệch lớn hơn 10%, hoặc năm gần nhất có lợi nhuận trước thuế âm, hệ thống tạo yêu cầu giải trình và không tự động kết luận hồ sơ đạt.',
      evaluation_basis: 'Làm căn cứ cho Financial Metrics và Tax Consistency; các trường annual_revenue, tax_declared_revenue và pretax_profit_last_2_years được đối chiếu ở đây.', content_hash: 'sha256:92ac310f11', quality_status: 'ACCEPTED', validation: 'VALID', reasons: [], related_nodes: ['FINANCIAL_METRICS', 'TAX_CONSISTENCY', 'MANDATORY_CRITIC'], case_field_refs: ['annual_revenue', 'tax_declared_revenue', 'pretax_profit_last_2_years'], provenance: { version: '2.4', owner: 'risk-policy' },
    },
    {
      chunk_id: `${context.case_id}-AML-03`, document_id: 'AML-POLICY-2026', document_number: 'AML-5.2',
      document_title: 'Chính sách KYC/AML SME', domain: 'AML', source_type: 'REGULATION', source_authority: 'Khối Tuân thủ',
      validity_status: 'EFFECTIVE', effective_date: '2026-02-10', article: 'Điều 5', clause: '5.2', page_or_part: 'Trang 21', citation_text: 'Mọi cờ về chủ sở hữu hưởng lợi hoặc giao dịch bất thường phải được Compliance Agent và cán bộ tuân thủ xác minh.',
      full_content: 'Điều 5.2 — Khi CaseContext có một hoặc nhiều kyc_aml_flags, Compliance Agent phải được route vào workflow. Kết quả là REVIEW_REQUIRED cho đến khi cán bộ tuân thủ xác minh nguồn và chủ sở hữu hưởng lợi.',
      evaluation_basis: 'Làm căn cứ kích hoạt Compliance Agent và đề xuất ESCALATE_TO_COMPLIANCE; không dùng để tự động kết luận vi phạm.', content_hash: 'sha256:4bc31df912', quality_status: 'ACCEPTED', validation: 'VALID', reasons: [], related_nodes: ['COMPLIANCE_AGENT', 'MANDATORY_CRITIC', 'POLICY_GATE'], case_field_refs: ['kyc_aml_flags', 'customer_id'], provenance: { version: '2026.02', owner: 'compliance' },
    },
    {
      chunk_id: `${context.case_id}-CIC-04`, document_id: 'CREDIT-RISK-GATE', document_number: 'CRG-7.1',
      document_title: 'Quy tắc kiểm soát CIC và dòng tiền', domain: 'LENDING', source_type: 'INTERNAL_POLICY', source_authority: 'Khối Quản trị rủi ro tín dụng',
      validity_status: 'EFFECTIVE', effective_date: '2026-03-01', article: 'Mục 7', clause: '7.1', page_or_part: 'Trang 31', citation_text: 'Cờ nợ xấu CIC là điều kiện chặn; vòng quay tài khoản thấp cần giải trình trước khi chuyển Human-in-the-loop.',
      full_content: 'Mục 7.1 — Nếu cic_bad_debt = true, Credit Agent phải trả về BLOCKED và Policy Gate phải chuyển hồ sơ tới chuyên viên. Với sản phẩm thấu chi, vòng quay tài khoản thấp hơn ngưỡng sản phẩm tạo cảnh báo và yêu cầu giải trình dòng tiền.',
      evaluation_basis: 'Làm căn cứ cho Credit Agent, Account Turnover và Policy Gate. Hệ thống chỉ tạo readiness blocker, không thay thế quyết định tín dụng của con người.', content_hash: 'sha256:18ef50aa21', quality_status: 'ACCEPTED', validation: 'VALID', reasons: [], related_nodes: ['ACCOUNT_TURNOVER', 'CREDIT_AGENT', 'READINESS_RULE_ENGINE', 'POLICY_GATE'], case_field_refs: ['cic_bad_debt', 'requested_amount', 'metadata'], provenance: { version: '7.1', owner: 'credit-risk' },
    },
    {
      chunk_id: `${context.case_id}-DEMO-05`, document_id: 'DEMO-GUIDE', document_number: 'DEMO-2026',
      document_title: 'Demo policy — Human in the loop', domain: 'DEMO_POLICY', source_type: 'DEMO_CONTENT', source_authority: 'Demo Content',
      validity_status: 'DEMO_ONLY', effective_date: '2026-07-01', page_or_part: 'Demo note', citation_text: 'Hệ thống chỉ đề xuất bước xử lý tiếp theo và không tự động phê duyệt hoặc từ chối khoản vay.',
      full_content: 'Demo note — Agent Layer tạo readiness artifacts, giải thích bằng chứng và đề xuất HITL. Việc phê duyệt hoặc từ chối khoản vay luôn nằm ngoài phạm vi tự động hóa của browser.',
      evaluation_basis: 'Dùng để giải thích ranh giới an toàn của prototype; không được dùng làm căn cứ pháp lý hoặc chính sách tín dụng.', content_hash: 'sha256:3ac1d73e11', quality_status: 'DEMO_ONLY', validation: 'WARNING_DEMO_ONLY', reasons: ['Nguồn chỉ dùng cho môi trường demo.'], related_nodes: ['PRODUCT_AGENT', 'CITATION_VALIDATOR', 'POLICY_GATE'], case_field_refs: [], provenance: { version: '2026-demo', owner: 'product-demo' },
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
    cic_bad_debt: false, kyc_aml_flags: [], metadata: { industry: 'Sản xuất bao bì', branch: 'ICTU Hà Nội', currency: 'VND', turnover_alert: 'true' },
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
  makeReadinessCase({
    case_id: 'CASE-WC-2026-0104', customer_id: 'CUS-NEW-0088', existing_customer: false, product: 'WORKING_CAPITAL', requested_amount: 7_500_000_000,
    relationship_months: 0, submitted_documents: ['BUSINESS_REGISTRATION', 'FINANCIAL_STATEMENTS_2Y', 'WORKING_CAPITAL_PLAN'], required_documents: REQUIRED_WORKING_CAPITAL,
    annual_revenue: 16_500_000_000, pretax_profit_last_2_years: [420_000_000, -180_000_000], tax_declared_revenue: 14_200_000_000,
    cic_bad_debt: false, kyc_aml_flags: ['NEW_CUSTOMER_KYC_PENDING'], metadata: { industry: 'Thương mại nông sản', branch: 'ICTU Thái Nguyên', currency: 'VND' },
  }, 'Công ty TNHH Nông sản An Phú', 'Đỗ Khánh Linh', '2026-07-16T08:40:00.000Z'),
]

export const documentOptions = {
  CORPORATE_OVERDRAFT: REQUIRED_OVERDRAFT,
  WORKING_CAPITAL: REQUIRED_WORKING_CAPITAL,
} as const
