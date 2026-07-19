import { AlertTriangle, ArrowLeft, BookOpen, Check, ChevronRight, CircleAlert, Clock3, FileDown, FileText, Gauge, ListTree, Send, ShieldCheck, UserCheck, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { NODE_LABELS, type EvidenceItem } from '../domain'
import { useReadiness } from '../readiness-context'
import { ArtifactPill, FinalStatusPill, ProductPill } from '../components/Status'
import { WorkflowCanvas } from '../components/WorkflowCanvas'
import { readinessApi, type LoanApprovalStatus } from '../api'
import { useAuth } from '../auth-context'

const money = (value: number | null) => value === null ? 'Chưa cung cấp' : `${new Intl.NumberFormat('vi-VN').format(value)} ₫`

function warningEvidence(evidence: EvidenceItem[], node: string, warning: string) {
  const code = warning.toUpperCase()
  const documentId = code.includes('TAX') ? 'SME-TAX-GUIDE'
    : code.includes('AML') || code.includes('KYC') || code.includes('BENEFICIAL_OWNER') ? 'AML-POLICY-2026'
    : code.includes('CIC') || code.includes('COLLATERAL') || code.includes('CREDIT') ? 'CREDIT-RISK-GATE'
    : null
  return (documentId ? evidence.find((item) => item.document_id === documentId) : undefined)
    ?? evidence.find((item) => item.related_nodes.includes(node) && item.domain !== 'CASE_DATA')
    ?? evidence.find((item) => item.domain === 'CASE_DATA')
}

function warningLabel(warning: string) {
  return warning.replace(/^LIVE_CRITIC:/, '').replace(/^UNRESOLVED_ARTIFACT:/, 'Chưa xử lý: ').replaceAll('_', ' ')
}

export function CaseDetailPage() {
  const { caseId } = useParams()
  const location = useLocation()
  const { cases, isLoading, rerunCase } = useReadiness()
  const { user } = useAuth()
  const [hitlMessage, setHitlMessage] = useState('')
  const [approval, setApproval] = useState<LoanApprovalStatus | null>(null)
  const [approvalReason, setApprovalReason] = useState('')
  const [approvalBusy, setApprovalBusy] = useState(false)
  const [approvalError, setApprovalError] = useState('')
  const [workflowVerified, setWorkflowVerified] = useState(() => window.sessionStorage.getItem(`workflow-verified:${caseId}`) === 'true')
  const item = cases.find((entry) => entry.id === caseId)
  useEffect(() => {
    if (!item || !location.hash) return
    const timer = window.setTimeout(() => document.getElementById(location.hash.slice(1))?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 80)
    return () => window.clearTimeout(timer)
  }, [item, location.hash])
  useEffect(() => setWorkflowVerified(window.sessionStorage.getItem(`workflow-verified:${caseId}`) === 'true'), [caseId])
  useEffect(() => {
    if (!caseId) return
    const controller = new AbortController()
    readinessApi.loanApproval(caseId, controller.signal).then(setApproval).catch((reason: unknown) => {
      if (reason instanceof DOMException && reason.name === 'AbortError') return
      setApprovalError(reason instanceof Error ? reason.message : 'Không thể tải trạng thái phê duyệt')
    })
    return () => controller.abort()
  }, [caseId, item?.workflow.final_status, item?.workflow.critic_verdict])
  if (isLoading) return <main className="page not-found"><h1>Đang tải hồ sơ...</h1><p>Backend đang chuẩn bị WorkflowState và evidence.</p></main>
  if (!item) return <main className="page not-found"><h1>Không tìm thấy hồ sơ</h1><Link className="primary-button" to="/">Về dashboard</Link></main>
  const { context, workflow } = item
  const missing = context.required_documents.filter((document) => !context.submitted_documents.includes(document))
  const artifacts = workflow.route.map((node) => workflow.artifacts[node]).filter(Boolean)
  const taxGap = context.annual_revenue && context.tax_declared_revenue !== null ? Math.abs(context.annual_revenue - context.tax_declared_revenue) / context.annual_revenue : null
  const refreshApproval = async () => setApproval(await readinessApi.loanApproval(item.id))
  const approveLoan = async () => {
    setApprovalBusy(true); setApprovalError('')
    try { await readinessApi.approveLoan(item.id, approvalReason); await refreshApproval() }
    catch (reason) { setApprovalError(reason instanceof Error ? reason.message : 'Không thể phê duyệt hồ sơ') }
    finally { setApprovalBusy(false) }
  }
  const transferLoan = async () => {
    setApprovalBusy(true); setApprovalError('')
    try { await readinessApi.transferLoan(item.id, approvalReason || 'Vượt hạn mức phê duyệt của cấp hiện tại'); setApprovalReason(''); await refreshApproval() }
    catch (reason) { setApprovalError(reason instanceof Error ? reason.message : 'Không thể chuyển cấp hồ sơ') }
    finally { setApprovalBusy(false) }
  }

  return <main className="case-workbench">
    <div className="case-topline"><Link to="/"><ArrowLeft size={15} /> Hàng đợi</Link><div><span>Case ID</span><strong>{item.id}</strong></div><FinalStatusPill status={workflow.final_status} /></div>
    <section className="case-hero" id="issue-customer"><div><ProductPill product={context.product} /><h1>{item.company_name}</h1><p><UserRound size={13} /> {item.owner} · {context.metadata.branch}</p></div><div className="hero-amount"><span>Giá trị đề nghị</span><strong>{money(context.requested_amount)}</strong><small>{context.metadata.industry}</small></div><div className="hero-sla"><Clock3 size={15} /><span>SLA</span><strong>{item.sla_due}</strong></div></section>
    <section className="safety-banner"><ShieldCheck size={18} /><div><strong>Chỉ đánh giá mức độ sẵn sàng</strong><span>AI tạo kết quả và đề xuất chuyển chuyên viên; không phê duyệt hoặc từ chối khoản vay.</span></div><span>Phản biện: <b>{workflow.critic_verdict}</b></span></section>
    <WorkflowCanvas context={context} workflow={workflow} evidence={item.evidence} onRun={(onNodeResult) => rerunCase(item.id, onNodeResult)} onRunComplete={() => { setWorkflowVerified(true); window.sessionStorage.setItem(`workflow-verified:${item.id}`, 'true') }} />
    <div className="workbench-grid"><div className="workbench-main">
      <section className="work-card" id="issue-financial"><div className="section-title"><div><Gauge size={17} /><h2>Input readiness</h2></div><span>CaseContext</span></div><div className="input-metrics"><article><span>Khách hàng hiện hữu</span><strong>{context.existing_customer ? 'Có' : 'Không'}</strong></article><article><span>Quan hệ</span><strong>{context.relationship_months} tháng</strong></article><article><span>Doanh thu năm</span><strong>{money(context.annual_revenue)}</strong></article><article><span>Doanh thu khai thuế</span><strong>{money(context.tax_declared_revenue)}</strong></article><article><span>Chênh lệch thuế</span><strong className={taxGap && taxGap > .1 ? 'text-warning' : ''}>{taxGap === null ? 'N/A' : `${(taxGap * 100).toFixed(1)}%`}</strong></article><article><span>CIC</span><strong className={context.cic_bad_debt ? 'text-danger' : ''}>{context.cic_bad_debt ? 'Có nợ xấu' : 'Không có cờ xấu'}</strong></article></div><div className="profit-block"><span>Lợi nhuận trước thuế 2 năm</span>{context.pretax_profit_last_2_years.map((value, index) => <div key={index}><small>Năm {index + 1}</small><strong>{money(value)}</strong><i style={{ width: `${Math.min(100, Math.abs(value) / Math.max(...context.pretax_profit_last_2_years.map(Math.abs), 1) * 100)}%` }} /></div>)}</div></section>
      <section className="work-card" id="issue-artifacts"><div className="section-title"><div><ListTree size={17} /><h2>Agent artifacts</h2></div><span>{artifacts.length} kết quả</span></div><div className="artifact-list">{artifacts.map((artifact) => <article key={artifact.agent_id}><div className="artifact-head"><div><strong>{NODE_LABELS[artifact.agent_id] ?? artifact.agent_id}</strong><span>{artifact.engine}</span></div><ArtifactPill status={artifact.status} /></div><p>{artifact.summary}</p>{Object.keys(artifact.metrics).length > 0 && <div className="artifact-metrics">{Object.entries(artifact.metrics).map(([key, value]) => <span key={key}>{key.replaceAll('_', ' ')}: <b>{value < 1 ? `${(value * 100).toFixed(1)}%` : new Intl.NumberFormat('vi-VN').format(value)}</b></span>)}</div>}{artifact.warnings.length > 0 && <div className="artifact-warnings">{artifact.warnings.map((warning) => { const source = warningEvidence(item.evidence, artifact.agent_id, warning); return source ? <Link key={warning} to={`/citations/${item.id}/${encodeURIComponent(source.chunk_id)}`} state={{ issueTarget: 'issue-artifacts' }}><AlertTriangle size={12} /><span>{warningLabel(warning)}</span><small>Xem căn cứ</small></Link> : <span key={warning}><AlertTriangle size={12} />{warningLabel(warning)}</span> })}</div>}</article>)}</div></section>
      <section className="work-card trace-summary"><div className="section-title"><div><ListTree size={17} /><h2>Nhật ký thực thi</h2></div><Link to="/trace">Xem toàn bộ <ChevronRight size={14} /></Link></div>{workflow.trace.slice(-5).map((event) => <div className="trace-line" key={event.node}><i /><div><strong>{NODE_LABELS[event.node] ?? event.node}</strong><span>{event.message}</span></div><time>{event.duration_ms} mili giây</time></div>)}</section>
    </div><aside className="workbench-side">
      <section className="side-card" id="issue-documents"><div className="side-card-title"><FileText size={17} /><h2>Document completeness</h2><strong>{context.submitted_documents.length}/{context.required_documents.length}</strong></div><div className="document-list">{context.required_documents.map((document) => { const complete = context.submitted_documents.includes(document); return <div key={document} className={complete ? 'complete' : 'missing'}><span>{complete ? <Check size={12} /> : <CircleAlert size={12} />}</span><strong>{document.replaceAll('_', ' ')}</strong><small>{complete ? 'Đã nộp' : 'Còn thiếu'}</small></div> })}</div>{missing.length > 0 && <button onClick={() => setHitlMessage(`Đã tạo yêu cầu bổ sung ${missing.length} tài liệu.`)} className="outline-button full-button">Yêu cầu bổ sung tài liệu</button>}{hitlMessage && <p className="hitl-feedback"><Check size={13} />{hitlMessage}</p>}</section>
      <section className="side-card" id="issue-evidence"><div className="side-card-title"><BookOpen size={17} /><h2>Evidence & citations</h2><Link className="citation-library-link" to={`/citations/${item.id}`}>Xem tất cả {item.evidence.length}</Link></div>{item.evidence.map((evidence) => <Link to={`/citations/${item.id}/${encodeURIComponent(evidence.chunk_id)}`} className="evidence-item evidence-link" key={evidence.chunk_id}><div><span className={`quality ${evidence.quality_status.toLowerCase()}`}>{evidence.quality_status}</span><small>{evidence.domain}</small></div><blockquote>“{evidence.citation_text}”</blockquote><strong>{evidence.document_title}</strong><span>{evidence.document_number} · {evidence.source_authority}</span><div className="citation-validation"><ShieldCheck size={12} />{evidence.validation}<ChevronRight size={12} /></div></Link>)}</section>
      <section className="side-card approval-card" id="issue-hitl"><div className="side-card-title"><UserCheck size={17} /><h2>Quyết định của người duyệt</h2></div>{approval ? <><div className="approval-levels"><div><span>Người đăng nhập</span><strong>{user?.role_name ?? user?.role_id}</strong></div><div><span>Cấp đang xử lý</span><strong>{approval.current_role}</strong></div><div><span>Cấp yêu cầu</span><strong>{approval.required_role}</strong></div></div>{approval.status === 'APPROVED' ? <div className="approval-success"><Check size={15} /> Hồ sơ đã được phê duyệt</div> : approval.blockers.length ? <div className="approval-blockers">{approval.blockers.map((blocker) => <span key={blocker}><CircleAlert size={12} />{blocker}</span>)}</div> : <><textarea value={approvalReason} onChange={(event) => setApprovalReason(event.target.value)} placeholder="Ý kiến hoặc lý do quyết định..." />{approval.can_approve && <button disabled={approvalBusy} onClick={approveLoan} className="primary-button full-button"><UserCheck size={14} />{approvalBusy ? 'Đang xử lý...' : 'Phê duyệt hồ sơ'}</button>}{approval.can_transfer && <button disabled={approvalBusy} onClick={transferLoan} className="outline-button full-button"><Send size={14} />{approvalBusy ? 'Đang chuyển...' : 'Chuyển lên cấp tiếp theo'}</button>}{!approval.can_approve && !approval.can_transfer && <p>Hồ sơ đang chờ người dùng thuộc cấp <b>{approval.current_role}</b> xử lý.</p>}</>}</> : <p>Đang tải quyền phê duyệt...</p>}{approvalError && <div className="approval-error"><AlertTriangle size={12} />{approvalError}</div>}</section>
      <section className={`side-card report-ready-card ${workflowVerified ? 'verified' : ''}`}><div className="side-card-title"><FileDown size={17} /><h2>Báo cáo doanh nghiệp</h2></div><p>{workflowVerified ? 'Workflow đã kiểm chứng xong. Có thể tạo báo cáo yêu cầu bổ sung để gửi doanh nghiệp.' : 'Hãy chạy hoàn tất workflow trước khi xuất báo cáo chính thức.'}</p>{workflowVerified ? <Link className="primary-button full-button" to={`/reports/${item.id}`}><FileText size={14} /> Tạo báo cáo bổ sung</Link> : <button className="outline-button full-button" disabled><Clock3 size={14} /> Chờ kiểm chứng hoàn tất</button>}</section>
    </aside></div>
  </main>
}
