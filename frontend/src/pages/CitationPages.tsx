import { ArrowLeft, ArrowRight, BookOpen, CalendarDays, CheckCircle2, ExternalLink, FileCheck2, Fingerprint, Landmark, Link2, Quote, Scale, ShieldCheck } from 'lucide-react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { NODE_LABELS, type CaseContext, type EvidenceItem } from '../domain'
import { useReadiness } from '../readiness-context'

const SOURCE_LABELS: Record<EvidenceItem['source_type'], string> = {
  CASE_RECORD: 'Dữ liệu hồ sơ khách hàng', INTERNAL_POLICY: 'Chính sách nội bộ', REGULATION: 'Quy định tuân thủ', DEMO_CONTENT: 'Nội dung mô phỏng',
}

const FIELD_LABELS: Record<string, string> = {
  case_id: 'Mã hồ sơ', relationship_months: 'Thời gian quan hệ', current_assets: 'Tài sản ngắn hạn', current_liabilities: 'Nợ ngắn hạn', total_debt: 'Tổng dư nợ', total_assets: 'Tổng tài sản',
  operating_cash_flow: 'Dòng tiền từ hoạt động kinh doanh', annual_debt_service: 'Nghĩa vụ trả nợ năm', collateral_ratio: 'Tỷ lệ tài sản bảo đảm', twelve_month_account_turnover: 'Vòng quay tài khoản 12 tháng',
  account_history_months: 'Lịch sử tài khoản', twelve_month_credit_turnover: 'Doanh số ghi Có 12 tháng', average_monthly_credit_inflow: 'Dòng tiền ghi Có bình quân tháng', turnover_stability_ratio: 'Độ ổn định dòng tiền',
  expected_utilization_ratio: 'Tỷ lệ sử dụng dự kiến', negative_balance_days: 'Số ngày sử dụng thấu chi', cleanup_days: 'Số ngày hoàn trả', overdraft_purpose: 'Mục đích thấu chi', loan_purpose: 'Mục đích vay', account_conduct_flags: 'Cảnh báo hành vi tài khoản',
  existing_customer: 'Khách hàng hiện hữu', product: 'Sản phẩm', requested_amount: 'Số tiền đề nghị', submitted_documents: 'Tài liệu đã nộp', required_documents: 'Tài liệu bắt buộc',
  annual_revenue: 'Doanh thu năm', tax_declared_revenue: 'Doanh thu khai thuế', pretax_profit_last_2_years: 'Lợi nhuận trước thuế 2 năm', cic_bad_debt: 'Cờ nợ xấu CIC',
  kyc_aml_flags: 'Cảnh báo KYC/AML', customer_id: 'Mã khách hàng', metadata: 'Thông tin bổ sung',
}

const VALUE_LABELS: Record<string, string> = {
  WORKING_CAPITAL: 'Vốn lưu động', CORPORATE_OVERDRAFT: 'Thấu chi doanh nghiệp',
  BUSINESS_REGISTRATION: 'Đăng ký kinh doanh', FINANCIAL_STATEMENTS_2Y: 'Báo cáo tài chính 2 năm', TAX_RETURNS_2Y: 'Tờ khai thuế 2 năm', CIC_REPORT: 'Báo cáo CIC',
  WORKING_CAPITAL_PLAN: 'Phương án vốn lưu động', BANK_STATEMENTS_12M: 'Sao kê tài khoản 12 tháng', OVERDRAFT_REQUEST: 'Đề nghị cấp hạn mức thấu chi', KYC: 'Hồ sơ định danh khách hàng',
  BENEFICIAL_OWNER_REVIEW: 'Cần xác minh chủ sở hữu hưởng lợi', NEW_CUSTOMER_KYC_PENDING: 'Khách hàng mới đang chờ hoàn tất KYC', IRREGULAR_CLEANUP: 'Chu kỳ hoàn trả không ổn định',
}

const MONEY_FIELDS = new Set(['requested_amount', 'annual_revenue', 'tax_declared_revenue', 'current_assets', 'current_liabilities', 'total_debt', 'total_assets', 'operating_cash_flow', 'annual_debt_service', 'twelve_month_account_turnover', 'twelve_month_credit_turnover', 'average_monthly_credit_inflow'])
const RATIO_FIELDS = new Set(['collateral_ratio', 'turnover_stability_ratio', 'expected_utilization_ratio'])

function formatCaseValue(field: string, value: unknown): string {
  if (value === null || value === undefined) return 'Chưa có dữ liệu'
  if (typeof value === 'boolean') return value ? 'Có' : 'Không'
  if (typeof value === 'number') {
    if (MONEY_FIELDS.has(field) || field.includes('profit')) return `${new Intl.NumberFormat('vi-VN').format(value)} ₫`
    if (RATIO_FIELDS.has(field)) return `${(value * 100).toFixed(1)}%`
    if (field.includes('months')) return `${new Intl.NumberFormat('vi-VN').format(value)} tháng`
    return new Intl.NumberFormat('vi-VN').format(value)
  }
  if (Array.isArray(value)) return value.length ? value.map((item) => typeof item === 'number' ? `${new Intl.NumberFormat('vi-VN').format(item)} ₫` : VALUE_LABELS[String(item)] ?? String(item).replaceAll('_', ' ')).join(' · ') : 'Không có cảnh báo'
  if (typeof value === 'object') return Object.entries(value as Record<string, unknown>).map(([key, item]) => `${FIELD_LABELS[key] ?? key.replaceAll('_', ' ')}: ${formatCaseValue(key, item)}`).join(' · ')
  return VALUE_LABELS[String(value)] ?? String(value).replaceAll('_', ' ')
}

function CaseContextContent({ context }: { context: CaseContext }) {
  const groups = [
    { title: 'Thông tin hồ sơ', fields: ['case_id', 'customer_id', 'product', 'existing_customer', 'relationship_months', 'requested_amount', 'loan_purpose', 'overdraft_purpose'] },
    { title: 'Hồ sơ và chứng từ', fields: ['submitted_documents', 'required_documents'] },
    { title: 'Tình hình tài chính', fields: ['annual_revenue', 'tax_declared_revenue', 'pretax_profit_last_2_years', 'current_assets', 'current_liabilities', 'total_debt', 'total_assets', 'operating_cash_flow', 'annual_debt_service', 'collateral_ratio'] },
    { title: 'Dòng tiền và tài khoản', fields: ['account_history_months', 'twelve_month_account_turnover', 'twelve_month_credit_turnover', 'average_monthly_credit_inflow', 'turnover_stability_ratio', 'expected_utilization_ratio', 'negative_balance_days', 'cleanup_days', 'account_conduct_flags'] },
    { title: 'Rủi ro và tuân thủ', fields: ['cic_bad_debt', 'kyc_aml_flags'] },
    { title: 'Thông tin bổ sung', fields: ['metadata'] },
  ]
  return <div className="case-context-readable">{groups.map((group) => <section key={group.title}><h3>{group.title}</h3><div className="citation-case-fields">{group.fields.map((field) => { const value = getCaseField(context, field); const missing = isMissingCaseValue(value); return <div className={missing ? 'missing-value' : ''} key={field}><span>{FIELD_LABELS[field] ?? field.replaceAll('_', ' ')}</span><strong>{formatCaseValue(field, value)}</strong>{missing && <small>Thông tin chưa được cung cấp</small>}</div> })}</div></section>)}</div>
}

function getCaseField(context: CaseContext, field: string) {
  return context[field as keyof CaseContext]
}

function isMissingCaseValue(value: unknown) {
  return value === null || value === undefined || (typeof value === 'string' && value.trim() === '')
}

function issueTarget(evidence: EvidenceItem) {
  if (evidence.domain === 'CASE_DATA') return 'issue-customer'
  if (evidence.document_id === 'SME-TAX-GUIDE') return 'issue-financial'
  if (evidence.document_id === 'AML-POLICY-2026' || evidence.document_id === 'CREDIT-RISK-GATE') return 'issue-artifacts'
  if (evidence.document_id === 'DEMO-GUIDE') return 'issue-hitl'
  return 'issue-evidence'
}

function CitationCard({ item, caseId }: { item: EvidenceItem; caseId: string }) {
  return <Link className="citation-library-card" to={`/citations/${caseId}/${encodeURIComponent(item.chunk_id)}`}><div className="citation-card-head"><span className={`citation-domain ${item.domain.toLowerCase()}`}>{item.domain.replaceAll('_', ' ')}</span><span>{item.validation}</span></div><h2>{item.document_title}</h2><p>“{item.citation_text}”</p><div><span>{item.document_number}</span><span>{item.source_authority}</span><ArrowRight size={15} /></div></Link>
}

export function CitationLibraryPage() {
  const { caseId } = useParams()
  const { cases } = useReadiness()
  const item = cases.find((entry) => entry.id === caseId)
  if (!item) return <main className="page not-found"><h1>Không tìm thấy hồ sơ nguồn</h1><Link to="/" className="primary-button">Về dashboard</Link></main>
  return <main className="page citation-library-page"><Link className="back-link" to={`/cases/${item.id}`}><ArrowLeft size={15} /> Quay lại hồ sơ</Link><div className="page-heading"><div><p className="eyebrow">EVIDENCE LIBRARY</p><h1>Thư viện trích dẫn</h1><p>{item.company_name} · {item.id} · {item.evidence.length} nguồn được sử dụng</p></div></div><div className="citation-library-grid">{item.evidence.map((evidence) => <CitationCard item={evidence} caseId={item.id} key={evidence.chunk_id} />)}</div></main>
}

export function CitationDetailPage() {
  const { caseId, chunkId } = useParams()
  const { cases } = useReadiness()
  const location = useLocation()
  const readinessCase = cases.find((entry) => entry.id === caseId)
  const evidence = readinessCase?.evidence.find((entry) => entry.chunk_id === decodeURIComponent(chunkId ?? ''))
  if (!readinessCase || !evidence) return <main className="page not-found"><h1>Không tìm thấy trích dẫn</h1><Link to={caseId ? `/citations/${caseId}` : '/'} className="primary-button">Về thư viện nguồn</Link></main>
  const index = readinessCase.evidence.findIndex((entry) => entry.chunk_id === evidence.chunk_id)
  const previous = readinessCase.evidence[index - 1]
  const next = readinessCase.evidence[index + 1]

  const returnTarget = (location.state as { issueTarget?: string } | null)?.issueTarget ?? issueTarget(evidence)
  return <main className="citation-detail-page">
    <div className="citation-breadcrumb"><Link to={`/cases/${readinessCase.id}`}><ArrowLeft size={14} /> Hồ sơ</Link><span>/</span><Link to={`/citations/${readinessCase.id}`}>Thư viện trích dẫn</Link><span>/</span><strong>{evidence.document_number}</strong></div>
    <header className="citation-detail-hero"><div><div className="citation-title-meta"><span className={`citation-domain ${evidence.domain.toLowerCase()}`}>{evidence.domain.replaceAll('_', ' ')}</span><span className={`citation-validity ${evidence.validation.toLowerCase()}`}><ShieldCheck size={12} />{evidence.validation}</span></div><h1>{evidence.document_title}</h1><p>{evidence.document_number} · {SOURCE_LABELS[evidence.source_type]}</p></div><Link className="outline-button" to={`/cases/${readinessCase.id}#${returnTarget}`}><ExternalLink size={14} /> Xem dữ liệu được đánh giá</Link></header>
    <div className="citation-detail-grid"><article className="citation-document">
      <section className="exact-quote"><div><Quote size={18} /><span>Đoạn được hệ thống trích dẫn nguyên văn</span></div><blockquote>“{evidence.citation_text}”</blockquote><small>Chunk ID: {evidence.chunk_id}</small></section>
      <section className="citation-section"><div className="citation-section-title"><BookOpen size={17} /><div><h2>Nội dung đầy đủ của căn cứ</h2><p>Phần nội dung bao quanh trích dẫn để nhân viên hiểu đúng ngữ cảnh.</p></div></div>{evidence.domain === 'CASE_DATA' ? <CaseContextContent context={readinessCase.context} /> : <p className="full-policy-content">{evidence.full_content}</p>}</section>
      <section className="citation-section evaluation-basis"><div className="citation-section-title"><Scale size={17} /><div><h2>Cơ sở dùng để đánh giá</h2><p>Giải thích vì sao nguồn này được áp dụng cho hồ sơ.</p></div></div><p>{evidence.evaluation_basis}</p></section>
      <section className="citation-section"><div className="citation-section-title"><Link2 size={17} /><div><h2>Các khâu workflow sử dụng nguồn này</h2><p>Nguồn không được dùng ngoài các khâu được liệt kê.</p></div></div><div className="related-node-list">{evidence.related_nodes.map((node, nodeIndex) => <div key={node}><span>{nodeIndex + 1}</span><div><strong>{NODE_LABELS[node] ?? node}</strong><small>{node}</small></div><CheckCircle2 size={15} /></div>)}</div></section>
      <section className="citation-section"><div className="citation-section-title"><FileCheck2 size={17} /><div><h2>Dữ liệu hồ sơ được đối chiếu</h2><p>Giá trị thực tế mà agent so sánh với căn cứ trên.</p></div></div>{evidence.case_field_refs.length ? <div className="citation-case-fields">{evidence.case_field_refs.map((field) => <div key={field}><span>{FIELD_LABELS[field] ?? field}</span><strong>{formatCaseValue(field, getCaseField(readinessCase.context, field))}</strong></div>)}</div> : <div className="no-case-fields">Nguồn này chỉ mô tả ranh giới hệ thống, không trực tiếp đánh giá trường dữ liệu nào.</div>}</section>
      <nav className="citation-pagination">{previous ? <Link to={`/citations/${readinessCase.id}/${encodeURIComponent(previous.chunk_id)}`}><ArrowLeft size={14} /><span>Nguồn trước<strong>{previous.document_number}</strong></span></Link> : <span />}{next && <Link to={`/citations/${readinessCase.id}/${encodeURIComponent(next.chunk_id)}`}><span>Nguồn tiếp theo<strong>{next.document_number}</strong></span><ArrowRight size={14} /></Link>}</nav>
    </article><aside className="citation-metadata">
      <div className="metadata-title"><Landmark size={18} /><div><strong>Thông tin nguồn</strong><span>Provenance & validation</span></div></div>
      <dl><div><dt>Cơ quan/đơn vị ban hành</dt><dd>{evidence.source_authority}</dd></div><div><dt>Loại nguồn</dt><dd>{SOURCE_LABELS[evidence.source_type]}</dd></div><div><dt>Miền tri thức</dt><dd>{evidence.domain}</dd></div><div><dt>Điều khoản</dt><dd>{[evidence.article, evidence.clause].filter(Boolean).join(' · ') || 'Không áp dụng'}</dd></div><div><dt>Trang/phần</dt><dd>{evidence.page_or_part ?? 'Không áp dụng'}</dd></div><div><dt>Ngày hiệu lực</dt><dd><CalendarDays size={12} />{evidence.effective_date}</dd></div><div><dt>Trạng thái hiệu lực</dt><dd>{evidence.validity_status}</dd></div><div><dt>Chất lượng nguồn</dt><dd>{evidence.quality_status}</dd></div></dl>
      <div className="hash-box"><Fingerprint size={15} /><div><span>Content hash</span><code>{evidence.content_hash}</code></div></div>
      <div className="validation-box"><ShieldCheck size={16} /><div><strong>{evidence.validation}</strong><span>{evidence.reasons.length ? evidence.reasons.join(' · ') : 'Quote, hash, authority và hiệu lực đã được kiểm tra.'}</span></div></div>
      <div className="provenance-box"><strong>Provenance</strong>{Object.entries(evidence.provenance).map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ')}</span><b>{value}</b></div>)}</div>
    </aside></div>
  </main>
}
