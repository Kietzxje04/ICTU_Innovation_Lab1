import {
  AlertTriangle, Bot, BrainCircuit, Check, ChevronDown, ChevronRight, CircleStop, Code2,
  ExternalLink, FileInput, FileOutput, GitBranch, LocateFixed, LoaderCircle, Maximize2,
  Minimize2, Minus, Play, Plus, RefreshCw, Route, ScrollText, ShieldCheck, Sparkles,
  Timer, XCircle, Zap,
} from 'lucide-react'
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { NODE_LABELS, PRODUCT_LABELS, type AgentArtifact, type CaseContext, type EvidenceItem, type ReadinessCase, type WorkflowState } from '../domain'
import { ArtifactPill } from './Status'

type RunnerStatus = 'idle' | 'running' | 'completed'
type NodeKind = 'business' | 'ai' | 'control'
type RuntimeResult = 'success' | 'warning' | 'error'

const renderNodeTransition = () => new Promise<void>((resolve) => {
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => window.setTimeout(resolve, 320))
  })
})

const AI_NODES = new Set(['PRODUCT_AGENT', 'CREDIT_AGENT', 'COMPLIANCE_AGENT', 'MANDATORY_CRITIC'])
const CONTROL_NODES = new Set(['READINESS_RULE_ENGINE', 'CITATION_VALIDATOR', 'POLICY_GATE'])

const FIELD_LABELS: Record<string, string> = {
  account_history_months: 'Lịch sử tài khoản', twelve_month_credit_turnover: 'Doanh số ghi Có 12 tháng', average_monthly_credit_inflow: 'Dòng tiền ghi Có bình quân tháng',
  requested_limit_to_monthly_inflow: 'Hạn mức đề nghị / dòng tiền tháng', turnover_stability_ratio: 'Độ ổn định dòng tiền', expected_utilization_ratio: 'Tỷ lệ sử dụng dự kiến',
  negative_balance_days: 'Số ngày dư nợ âm', cleanup_days: 'Số ngày hoàn trả', overdraft_purpose: 'Mục đích thấu chi', loan_purpose: 'Mục đích vay',
  account_conduct_flags: 'Cờ hành vi tài khoản', collateral_ratio: 'Tỷ lệ tài sản bảo đảm', recognized_documents: 'Tài liệu đã phân loại', policy_source: 'Nguồn chính sách',
  case_id: 'Mã hồ sơ', customer_id: 'Mã khách hàng', product: 'Sản phẩm', existing_customer: 'Khách hàng hiện hữu',
  relationship_months: 'Thời gian quan hệ', requested_amount: 'Số tiền đề nghị', metadata: 'Thông tin bổ sung',
  required_documents: 'Tài liệu bắt buộc', submitted_documents: 'Tài liệu đã nộp', source: 'Nguồn dữ liệu',
  annual_revenue: 'Doanh thu năm', pretax_profit_last_2_years: 'Lợi nhuận trước thuế 2 năm', tax_declared_revenue: 'Doanh thu khai thuế',
  cic_bad_debt: 'Cờ nợ xấu CIC', upstream_artifacts: 'Kết quả đầu vào liên quan', kyc_aml_flags: 'Cảnh báo KYC/AML', rag_namespace: 'Kho tri thức sử dụng',
  route: 'Quy trình xử lý', artifact_statuses: 'Trạng thái các khâu', artifacts_to_review: 'Các khâu cần Critic rà soát', max_rework: 'Số lần làm lại tối đa',
  citation_ids: 'Mã trích dẫn', checks: 'Các bước kiểm chứng', critic_verdict: 'Kết luận của Critic', citation_results: 'Kết quả kiểm chứng trích dẫn',
  final_status: 'Trạng thái readiness cuối', handoff: 'Bước chuyển tiếp', agent_id: 'Khâu xử lý', engine: 'Cơ chế xử lý', status: 'Trạng thái', summary: 'Kết luận dễ hiểu',
  claims: 'Các nhận định có dẫn chứng', metrics: 'Chỉ số tính toán', warnings: 'Vấn đề phát hiện', proposed_actions: 'Hành động đề xuất', raw: 'Dữ liệu kỹ thuật mở rộng',
  completeness_ratio: 'Tỷ lệ đầy đủ hồ sơ', average_monthly_turnover: 'Vòng quay trung bình tháng', latest_pretax_profit: 'Lợi nhuận gần nhất', tax_gap_ratio: 'Tỷ lệ chênh lệch thuế',
  validation_results: 'Kết quả xác thực nguồn', document_id: 'Mã tài liệu', chunk_id: 'Đoạn bằng chứng', claim_id: 'Mã nhận định', quote: 'Nội dung trích dẫn', claim_type: 'Loại nhận định',
}

const VALUE_LABELS: Record<string, string> = {
  CORPORATE_OVERDRAFT: 'Thấu chi doanh nghiệp', WORKING_CAPITAL: 'Vốn lưu động', PASS: 'Đạt', WARNING: 'Có cảnh báo', BLOCKED: 'Bị chặn', REVIEW_REQUIRED: 'Cần nhân viên rà soát',
  READY_FOR_HUMAN_REVIEW: 'Sẵn sàng chuyển nhân viên rà soát', NEEDS_MORE_EVIDENCE: 'Cần bổ sung bằng chứng', IN_PROGRESS: 'Đang xử lý',
  REVISE: 'Cần chỉnh sửa', ESCALATE: 'Chuyển cấp chuyên môn', PENDING: 'Đang chờ', DETERMINISTIC: 'Luật xử lý cố định', DETERMINISTIC_PLUS_LLM: 'Luật định kết hợp AI', RULES_PLUS_RAG: 'Luật định kết hợp kho tri thức',
  CLOUD_LLM_STRUCTURED: 'AI đám mây có cấu trúc', LOCAL_LLM_OR_DETERMINISTIC: 'AI nội bộ hoặc luật định', CLOUD_LLM: 'AI đám mây',
  HUMAN_REVIEW: 'Chuyển nhân viên phụ trách', VALID: 'Trích dẫn hợp lệ', WARNING_DEMO_ONLY: 'Nguồn chỉ dùng cho demo',
  exact_quote: 'Kiểm tra nguyên văn', content_hash: 'Kiểm tra toàn vẹn nội dung', authority: 'Kiểm tra thẩm quyền nguồn', validity: 'Kiểm tra hiệu lực',
  core_banking_mock: 'Dữ liệu Core Banking mô phỏng', AML: 'Kho tri thức phòng chống rửa tiền',
}

function getNodeKind(node: string): NodeKind {
  if (AI_NODES.has(node)) return 'ai'
  if (CONTROL_NODES.has(node)) return 'control'
  return 'business'
}

function getNodeDescription(node: string) {
  const descriptions: Record<string, string> = {
    DOCUMENT_CLASSIFIER: 'Chuẩn hóa loại tài liệu đã nộp theo vocabulary của Agent.', REQUIREMENT_MATRIX: 'Nạp danh mục hồ sơ bắt buộc từ cấu hình sản phẩm của Agent.',
    OVERDRAFT_METRICS: 'Tính chỉ số thấu chi quay vòng từ dòng tiền ghi Có và hạn mức đề nghị.', CIC_KYC_TOOLS: 'Đối chiếu tín hiệu CIC, KYC và AML trước khi tổng hợp readiness.',
    EXISTING_CUSTOMER_GATE: 'Xác nhận khách hàng có nằm trong phạm vi xử lý trước khi phân tích.', PRODUCT_AGENT: 'AI xác định sản phẩm và các điều kiện cần kiểm tra.',
    DOCUMENT_COMPLETENESS: 'Đối chiếu tài liệu đã nộp với danh mục bắt buộc.', ACCOUNT_TURNOVER: 'Đánh giá mức độ ổn định của dòng tiền tài khoản.',
    FINANCIAL_METRICS: 'Tổng hợp doanh thu và xu hướng lợi nhuận hai năm.', TAX_CONSISTENCY: 'Đối chiếu doanh thu báo cáo với doanh thu khai thuế.',
    CREDIT_AGENT: 'AI tổng hợp tín hiệu tín dụng và điểm cần nhân viên rà soát.', COMPLIANCE_AGENT: 'AI kết hợp RAG đánh giá các cờ KYC và AML.',
    READINESS_RULE_ENGINE: 'Áp dụng quy tắc để tìm điều kiện chặn và bằng chứng còn thiếu.', MANDATORY_CRITIC: 'AI Critic tìm mâu thuẫn, thiếu sót và yêu cầu làm lại khi cần.',
    CITATION_VALIDATOR: 'Kiểm tra nguyên văn, tính toàn vẹn, thẩm quyền và hiệu lực nguồn.', POLICY_GATE: 'Chốt trạng thái readiness và đề xuất bước Human-in-the-loop.',
  }
  return descriptions[node] ?? 'Xử lý một bước trong quy trình hybrid-agent.'
}

function getNodeInput(node: string, context: CaseContext, workflow: WorkflowState) {
  const common = { case_id: context.case_id, customer_id: context.customer_id, product: context.product }
  switch (node) {
    case 'EXISTING_CUSTOMER_GATE': return { ...common, existing_customer: context.existing_customer, relationship_months: context.relationship_months }
    case 'PRODUCT_AGENT': return { ...common, requested_amount: context.requested_amount, metadata: context.metadata }
    case 'DOCUMENT_COMPLETENESS': return { required_documents: context.required_documents, submitted_documents: context.submitted_documents }
    case 'DOCUMENT_CLASSIFIER': return { submitted_documents: context.submitted_documents }
    case 'REQUIREMENT_MATRIX': return { product: context.product, required_documents: context.required_documents }
    case 'ACCOUNT_TURNOVER': return { customer_id: context.customer_id, account_history_months: context.account_history_months, twelve_month_credit_turnover: context.twelve_month_credit_turnover, average_monthly_credit_inflow: context.average_monthly_credit_inflow }
    case 'OVERDRAFT_METRICS': return { requested_amount: context.requested_amount, twelve_month_credit_turnover: context.twelve_month_credit_turnover, average_monthly_credit_inflow: context.average_monthly_credit_inflow, turnover_stability_ratio: context.turnover_stability_ratio, expected_utilization_ratio: context.expected_utilization_ratio, negative_balance_days: context.negative_balance_days, cleanup_days: context.cleanup_days, account_conduct_flags: context.account_conduct_flags }
    case 'FINANCIAL_METRICS': return { annual_revenue: context.annual_revenue, pretax_profit_last_2_years: context.pretax_profit_last_2_years }
    case 'TAX_CONSISTENCY': return { annual_revenue: context.annual_revenue, tax_declared_revenue: context.tax_declared_revenue }
    case 'CREDIT_AGENT': return { requested_amount: context.requested_amount, cic_bad_debt: context.cic_bad_debt, upstream_artifacts: Object.keys(workflow.artifacts).filter((key) => ['FINANCIAL_METRICS', 'ACCOUNT_TURNOVER', 'TAX_CONSISTENCY'].includes(key)) }
    case 'COMPLIANCE_AGENT': return { kyc_aml_flags: context.kyc_aml_flags, rag_namespace: 'AML' }
    case 'CIC_KYC_TOOLS': return { cic_bad_debt: context.cic_bad_debt, kyc_aml_flags: context.kyc_aml_flags }
    case 'READINESS_RULE_ENGINE': return { route: workflow.route, artifact_statuses: Object.fromEntries(Object.entries(workflow.artifacts).map(([key, value]) => [key, value.status])) }
    case 'MANDATORY_CRITIC': return { artifacts_to_review: Object.keys(workflow.artifacts).filter((key) => key !== 'MANDATORY_CRITIC'), max_rework: 1 }
    case 'CITATION_VALIDATOR': return { citation_ids: Object.keys(workflow.citation_results), checks: ['exact_quote', 'content_hash', 'authority', 'validity'] }
    case 'POLICY_GATE': return { critic_verdict: workflow.critic_verdict, citation_results: workflow.citation_results }
    default: return common
  }
}

function getNodeOutput(node: string, artifact: AgentArtifact | undefined, workflow: WorkflowState) {
  if (node === 'POLICY_GATE') return { final_status: workflow.final_status, critic_verdict: workflow.critic_verdict, handoff: 'HUMAN_REVIEW' }
  if (node === 'CITATION_VALIDATOR') return { validation_results: workflow.citation_results, status: artifact?.status, summary: artifact?.summary }
  if (!artifact) return { status: 'PASS', summary: 'Khâu xử lý đã hoàn tất.' }
  return { status: artifact.status, summary: artifact.summary, metrics: artifact.metrics, warnings: artifact.warnings, proposed_actions: artifact.proposed_actions }
}

function formatPrimitive(field: string, value: string | number | boolean | null) {
  if (value === null) return 'Chưa có dữ liệu'
  if (typeof value === 'boolean') return value ? 'Có' : 'Không'
  if (typeof value === 'number') {
    if (field.includes('ratio')) return `${(value * 100).toFixed(1)}%`
    if (field.includes('amount') || field.includes('revenue') || field.includes('profit') || field.includes('turnover')) return `${new Intl.NumberFormat('vi-VN').format(value)} ₫`
    if (field === 'relationship_months') return `${value} tháng`
    return new Intl.NumberFormat('vi-VN').format(value)
  }
  return VALUE_LABELS[value] ?? NODE_LABELS[value] ?? PRODUCT_LABELS[value as keyof typeof PRODUCT_LABELS] ?? value.replaceAll('_', ' ')
}

function ReadableValue({ field, value }: { field: string; value: unknown }): ReactNode {
  if (Array.isArray(value)) return value.length ? <div className="readable-list">{value.map((item, index) => <span key={`${String(item)}-${index}`}>{typeof item === 'object' ? JSON.stringify(item) : formatPrimitive(field, item as string | number | boolean)}</span>)}</div> : <em>Không có</em>
  if (value && typeof value === 'object') return <div className="readable-object">{Object.entries(value as Record<string, unknown>).map(([key, child]) => <div key={key}><small>{FIELD_LABELS[key] ?? key.replaceAll('_', ' ')}</small><ReadableValue field={key} value={child} /></div>)}</div>
  return <strong>{formatPrimitive(field, value as string | number | boolean | null)}</strong>
}

function HumanDataPanel({ title, icon, data, tone }: { title: string; icon: ReactNode; data: Record<string, unknown>; tone?: 'output' }) {
  return <section className={`human-data-panel ${tone ?? ''}`}><div className="human-panel-title">{icon}<div><strong>{title}</strong><span>Diễn giải cho nhân viên nghiệp vụ</span></div></div><div className="human-fields">{Object.entries(data).map(([field, value]) => <div className="human-field" key={field}><label>{FIELD_LABELS[field] ?? field.replaceAll('_', ' ')}</label><ReadableValue field={field} value={value} /></div>)}</div></section>
}

function getIssueTarget(node: string) {
  if (node === 'EXISTING_CUSTOMER_GATE' || node === 'PRODUCT_AGENT') return 'issue-customer'
  if (['DOCUMENT_COMPLETENESS', 'DOCUMENT_CLASSIFIER', 'REQUIREMENT_MATRIX'].includes(node)) return 'issue-documents'
  if (['ACCOUNT_TURNOVER', 'OVERDRAFT_METRICS', 'FINANCIAL_METRICS', 'TAX_CONSISTENCY'].includes(node)) return 'issue-financial'
  if (['CIC_KYC_TOOLS', 'CREDIT_AGENT', 'COMPLIANCE_AGENT', 'READINESS_RULE_ENGINE', 'MANDATORY_CRITIC'].includes(node)) return 'issue-artifacts'
  if (node === 'CITATION_VALIDATOR') return 'issue-evidence'
  return 'issue-hitl'
}

function getNodeCitations(node: string, context: CaseContext, evidence: EvidenceItem[], artifact?: AgentArtifact) {
  const dataSource = evidence.find((item) => item.domain === 'CASE_DATA')
  const policyDocument = node === 'COMPLIANCE_AGENT' ? 'AML-POLICY-2026'
    : ['FINANCIAL_METRICS', 'TAX_CONSISTENCY'].includes(node) ? 'SME-TAX-GUIDE'
    : ['ACCOUNT_TURNOVER', 'CREDIT_AGENT'].includes(node) ? 'CREDIT-RISK-GATE'
    : ['READINESS_RULE_ENGINE', 'MANDATORY_CRITIC'].includes(node) ? 'SME-POLICY-V31'
    : ['CITATION_VALIDATOR', 'POLICY_GATE', 'PRODUCT_AGENT'].includes(node) ? 'DEMO-GUIDE'
    : 'SME-POLICY-V31'
  const policySource = evidence.find((item) => item.document_id === policyDocument) ?? evidence.find((item) => item.domain === 'LENDING')
  const target = getIssueTarget(node)
  return [dataSource, policySource].filter((item, index, items): item is EvidenceItem => Boolean(item) && items.findIndex((candidate) => candidate?.chunk_id === item?.chunk_id) === index).map((item) => ({
    id: item.chunk_id, source: item.document_title, reference: item.document_number, quote: item.citation_text, target,
    issue: Boolean(artifact && artifact.status !== 'PASS'),
  }))
}

export function WorkflowCanvas({ context, workflow, evidence, onRun, onRunComplete }: { context: CaseContext; workflow: WorkflowState; evidence: EvidenceItem[]; onRun: (onNodeResult: (state: WorkflowState, node: string, index: number) => void | Promise<void>) => Promise<ReadinessCase>; onRunComplete?: () => void }) {
  const [runnerStatus, setRunnerStatus] = useState<RunnerStatus>('idle')
  const [displayWorkflow, setDisplayWorkflow] = useState(workflow)
  const [activeIndex, setActiveIndex] = useState(-1)
  const [completedCount, setCompletedCount] = useState(0)
  const [runtimeResults, setRuntimeResults] = useState<Record<string, RuntimeResult>>({})
  const [selectedNode, setSelectedNode] = useState(workflow.route[0])
  const [elapsedMs, setElapsedMs] = useState(0)
  const [detailOpen, setDetailOpen] = useState(true)
  const [runtimeNotice, setRuntimeNotice] = useState('')
  const [runError, setRunError] = useState('')
  const [zoom, setZoom] = useState(.9)
  const [focusMode, setFocusMode] = useState(false)
  const runToken = useRef(0)
  const viewportRef = useRef<HTMLDivElement>(null)

  useEffect(() => () => { runToken.current += 1 }, [])
  useEffect(() => setDisplayWorkflow(workflow), [workflow])
  useEffect(() => {
    if (activeIndex < 0) return
    const viewport = viewportRef.current
    const node = viewport?.querySelector<HTMLElement>(`[data-node-index="${activeIndex}"]`)
    if (!viewport || !node) return
    viewport.scrollTo({ left: Math.max(0, node.offsetLeft - viewport.clientWidth / 2 + node.offsetWidth / 2), behavior: 'smooth' })
  }, [activeIndex])
  useEffect(() => {
    if (!focusMode) return
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') setFocusMode(false) }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [focusMode])
  useEffect(() => {
    if (runnerStatus !== 'running') return
    const startedAt = performance.now() - elapsedMs
    const timer = window.setInterval(() => setElapsedMs(performance.now() - startedAt), 100)
    return () => window.clearInterval(timer)
  }, [runnerStatus])

  const runWorkflow = async () => {
    const token = ++runToken.current
    setRunnerStatus('running'); setActiveIndex(0); setCompletedCount(0); setElapsedMs(0); setRuntimeResults({}); setRuntimeNotice('Backend Agent runtime đang thực thi route thật. Mỗi node chỉ chuyển tiếp sau khi nhận được kết quả runtime.'); setRunError('')
    const startedAt = performance.now()
    try {
      const result = await onRun(async (state, node, index) => {
        if (token !== runToken.current) return
        setDisplayWorkflow(state)
        const status = state.artifacts[node]?.status ?? 'PASS'
        const nodeResult: RuntimeResult = status === 'BLOCKED' ? 'error' : status === 'WARNING' || status === 'REVIEW_REQUIRED' ? 'warning' : 'success'
        setRuntimeResults((current) => ({ ...current, [node]: nodeResult }))
        setCompletedCount(index + 1)
        setSelectedNode(node); setDetailOpen(true)
        setActiveIndex(index + 1 < state.route.length ? index + 1 : -1)
        setRuntimeNotice(`${NODE_LABELS[node] ?? node} đã trả kết quả ${status}. ${index + 1 < state.route.length ? `Đang chuyển sang ${NODE_LABELS[state.route[index + 1]] ?? state.route[index + 1]}.` : 'Đang hoàn tất workflow.'}`)
        await renderNodeTransition()
      })
      if (token !== runToken.current) return
      const backendElapsedMs = performance.now() - startedAt
      setElapsedMs(backendElapsedMs)
      setActiveIndex(-1); setElapsedMs(backendElapsedMs); setRunnerStatus('completed')
      setRuntimeNotice('Agentic workflow đã hoàn tất từ kết quả backend thực tế, bao gồm Mandatory Critic và các control gate.')
      onRunComplete?.()
    } catch (reason) {
      if (token !== runToken.current) return
      setRunnerStatus('idle'); setRunError(reason instanceof Error ? reason.message : 'Không thể chạy agentic workflow'); setRuntimeNotice('')
    }
  }

  const resetWorkflow = () => { runToken.current += 1; setRunnerStatus('idle'); setActiveIndex(-1); setCompletedCount(0); setElapsedMs(0); setRuntimeResults({}); setRuntimeNotice(''); setRunError('') }
  const fitWorkflow = () => { setZoom(.8); viewportRef.current?.scrollTo({ left: 0, behavior: 'smooth' }) }
  const artifact = displayWorkflow.artifacts[selectedNode]
  const citations = getNodeCitations(selectedNode, context, evidence, artifact)
  const progress = workflow.route.length ? completedCount / workflow.route.length * 100 : 0

  return <section className={`work-card workflow-studio ${focusMode ? 'focus-mode' : ''}`}>
    <div className="workflow-studio-header"><div className="workflow-heading"><div className="workflow-logo"><Route size={18} /></div><div><h2>Visual Hybrid-Agent Workflow</h2><p>Nghiệp vụ, AI và khâu kiểm soát chạy theo route của hồ sơ</p></div></div><div className="runner-toolbar"><span className={`runner-state ${runnerStatus}`}><i />{runnerStatus === 'idle' ? 'Sẵn sàng' : runnerStatus === 'running' ? 'Đang thực thi' : 'Đã hoàn tất'}</span><span className="runner-time"><Timer size={13} />{(elapsedMs / 1000).toFixed(1)}s</span><div className="canvas-controls"><button onClick={() => setZoom((value) => Math.max(.65, value - .1))} aria-label="Thu nhỏ"><Minus size={13} /></button><span>{Math.round(zoom * 100)}%</span><button onClick={() => setZoom((value) => Math.min(1.2, value + .1))} aria-label="Phóng to"><Plus size={13} /></button><button onClick={fitWorkflow} aria-label="Vừa khung"><LocateFixed size={13} /></button><button onClick={() => setFocusMode((value) => !value)} aria-label="Chế độ tập trung">{focusMode ? <Minimize2 size={13} /> : <Maximize2 size={13} />}</button></div>{runnerStatus === 'completed' && <button className="runner-reset" onClick={resetWorkflow}><RefreshCw size={14} /> Đặt lại</button>}<button className="runner-play" disabled={runnerStatus === 'running'} onClick={runWorkflow}>{runnerStatus === 'running' ? <LoaderCircle className="spin" size={15} /> : <Play size={15} fill="currentColor" />}{runnerStatus === 'completed' ? 'Chạy lại' : runnerStatus === 'running' ? 'Đang chạy...' : 'Chạy workflow'}</button></div></div>
    <div className="runner-progress"><i style={{ width: `${progress}%` }} /></div>
    {runtimeNotice && <div className={`runtime-notice ${Object.values(runtimeResults).includes('error') ? 'error' : 'warning'}`}>{Object.values(runtimeResults).includes('error') ? <XCircle size={15} /> : <AlertTriangle size={15} />}<span>{runtimeNotice}</span></div>}
    {runError && <div className="runtime-notice error"><XCircle size={15} /><span>{runError}</span></div>}
    <div className="workflow-legend"><span><i className="business" /> Nghiệp vụ</span><span><i className="ai" /> AI / RAG</span><span><i className="control" /> Kiểm soát an toàn</span><small>Chọn node để xem dữ liệu và trích dẫn</small></div>
    <div className="workflow-canvas-viewport" ref={viewportRef}><div className="workflow-canvas-grid" /><div className="visual-pipeline" style={{ zoom } as CSSProperties}><div className={`terminal-node start ${runnerStatus !== 'idle' ? 'completed' : ''}`}><span><Zap size={15} /></span><strong>Tiếp nhận hồ sơ</strong><small>Kích hoạt quy trình</small></div>{workflow.route.map((node, index) => {
      const kind = getNodeKind(node); const isRunning = runnerStatus === 'running' && activeIndex === index; const isCompleted = completedCount > index; const isWaiting = runnerStatus === 'running' && activeIndex < index; const result = runtimeResults[node]; const NodeIcon = kind === 'ai' ? BrainCircuit : kind === 'control' ? ShieldCheck : GitBranch
      return <div className="pipeline-segment" key={node} data-node-index={index}><div className={`workflow-edge ${isRunning || isCompleted ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${result ?? ''}`}><span /><i /></div><button onClick={() => { setSelectedNode(node); setDetailOpen(true) }} className={`visual-node ${kind} ${isRunning ? 'running' : ''} ${isCompleted ? 'completed' : ''} ${result ?? ''} ${isWaiting ? 'waiting' : ''} ${selectedNode === node ? 'selected' : ''}`}><i className="port input-port" /><div className="node-top"><span className="node-icon">{isRunning ? <LoaderCircle className="spin" size={16} /> : result === 'error' ? <XCircle size={16} /> : result === 'warning' ? <AlertTriangle size={16} /> : isCompleted ? <Check size={16} /> : <NodeIcon size={16} />}</span><span className="node-kind">{kind === 'ai' ? 'AI AGENT' : kind === 'control' ? 'KIỂM SOÁT' : 'NGHIỆP VỤ'}</span><ChevronRight size={13} /></div><strong>{NODE_LABELS[node] ?? node}</strong><small>{workflow.artifacts[node]?.engine ?? 'DETERMINISTIC'}</small><div className="node-footer"><span>{isRunning ? 'Đang xử lý...' : result === 'error' ? 'Lỗi nghiệp vụ' : result === 'warning' ? 'Cần rà soát' : isCompleted ? 'Hoàn thành' : 'Chờ chạy'}</span>{AI_NODES.has(node) && <Sparkles size={11} />}</div><i className="port output-port" /></button></div>
    })}<div className="pipeline-segment"><div className={`workflow-edge ${runnerStatus === 'completed' ? 'active completed' : ''}`}><span /><i /></div><div className={`terminal-node end ${runnerStatus === 'completed' ? 'completed' : ''} ${workflow.final_status === 'BLOCKED' ? 'blocked' : ''}`}><span>{workflow.final_status === 'BLOCKED' && runnerStatus === 'completed' ? <XCircle size={15} /> : runnerStatus === 'completed' ? <Check size={15} /> : <CircleStop size={15} />}</span><strong>Chuyển nhân viên</strong><small>{VALUE_LABELS[workflow.final_status] ?? workflow.final_status}</small></div></div></div></div>
    <div className={`node-inspector ${detailOpen ? 'open' : ''}`}><button className="inspector-toggle" onClick={() => setDetailOpen((current) => !current)}><div><Code2 size={15} /><span>Chi tiết khâu xử lý</span><strong>{NODE_LABELS[selectedNode] ?? selectedNode}</strong></div><ChevronDown size={16} /></button>{detailOpen && <div className="inspector-content"><div className="inspector-summary"><div className={`inspector-icon ${getNodeKind(selectedNode)}`}>{getNodeKind(selectedNode) === 'ai' ? <Bot size={19} /> : getNodeKind(selectedNode) === 'control' ? <ShieldCheck size={19} /> : <GitBranch size={19} />}</div><div><div><span>{getNodeKind(selectedNode) === 'ai' ? 'KHÂU AI / RAG' : getNodeKind(selectedNode) === 'control' ? 'KHÂU KIỂM SOÁT' : 'KHÂU NGHIỆP VỤ'}</span>{artifact && <ArtifactPill status={artifact.status} />}</div><h3>{NODE_LABELS[selectedNode] ?? selectedNode}</h3><p>{getNodeDescription(selectedNode)}</p></div></div><div className="human-io-grid"><HumanDataPanel title="Dữ liệu được sử dụng" icon={<FileInput size={15} />} data={getNodeInput(selectedNode, context, workflow)} /><div className="io-arrow"><ChevronRight size={18} /></div><HumanDataPanel title="Kết quả của khâu" icon={<FileOutput size={15} />} data={getNodeOutput(selectedNode, artifact, workflow)} tone="output" /></div><aside className="node-citations"><div className="citation-heading"><ScrollText size={15} /><div><strong>Trích dẫn và nguồn</strong><span>Mở trang căn cứ đầy đủ</span></div></div>{citations.map((citation) => <Link key={citation.id} className={citation.issue ? 'has-issue' : ''} to={`/citations/${context.case_id}/${encodeURIComponent(citation.id)}`} state={{ issueTarget: citation.target }}><div><span>{citation.source}</span>{citation.issue && <b><AlertTriangle size={10} /> Có vấn đề</b>}</div><blockquote>“{citation.quote}”</blockquote><small>{citation.reference}<ExternalLink size={10} /></small></Link>)}</aside></div>}</div>
  </section>
}
