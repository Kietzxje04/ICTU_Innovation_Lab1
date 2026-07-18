import {
  Bot, BrainCircuit, Check, ChevronDown, ChevronRight, CircleStop, Code2, FileJson,
  GitBranch, LoaderCircle, Play, RefreshCw, Route, ShieldCheck, Sparkles, Timer, Zap,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { NODE_LABELS, type AgentArtifact, type CaseContext, type WorkflowState } from '../domain'
import { ArtifactPill } from './Status'

type RunnerStatus = 'idle' | 'running' | 'completed'
type NodeKind = 'business' | 'ai' | 'control'

const AI_NODES = new Set(['PRODUCT_AGENT', 'CREDIT_AGENT', 'COMPLIANCE_AGENT', 'MANDATORY_CRITIC'])
const CONTROL_NODES = new Set(['READINESS_RULE_ENGINE', 'CITATION_VALIDATOR', 'POLICY_GATE'])

function getNodeKind(node: string): NodeKind {
  if (AI_NODES.has(node)) return 'ai'
  if (CONTROL_NODES.has(node)) return 'control'
  return 'business'
}

function getNodeDescription(node: string) {
  const descriptions: Record<string, string> = {
    EXISTING_CUSTOMER_GATE: 'Xác nhận phạm vi khách hàng hiện hữu trước khi phân tích.',
    PRODUCT_AGENT: 'AI xác định đặc tính sản phẩm và các điều kiện cần đánh giá.',
    DOCUMENT_COMPLETENESS: 'Đối chiếu tài liệu đã nộp với danh mục bắt buộc.',
    ACCOUNT_TURNOVER: 'Tính toán vòng quay và mức độ ổn định của dòng tiền tài khoản.',
    FINANCIAL_METRICS: 'Tổng hợp doanh thu và xu hướng lợi nhuận hai năm.',
    TAX_CONSISTENCY: 'Đối chiếu doanh thu báo cáo với doanh thu khai thuế.',
    CREDIT_AGENT: 'AI tổng hợp tín hiệu tín dụng và điểm cần cán bộ rà soát.',
    COMPLIANCE_AGENT: 'AI/RAG đánh giá các cờ KYC và AML được kích hoạt.',
    READINESS_RULE_ENGINE: 'Áp dụng các quy tắc readiness xác định blocker và evidence gap.',
    MANDATORY_CRITIC: 'AI Critic tìm mâu thuẫn, thiếu sót và yêu cầu rework khi cần.',
    CITATION_VALIDATOR: 'Kiểm tra quote, hash, authority và trạng thái hiệu lực của bằng chứng.',
    POLICY_GATE: 'Chốt trạng thái readiness và đề xuất bước Human-in-the-loop.',
  }
  return descriptions[node] ?? 'Xử lý một bước trong hybrid-agent workflow.'
}

function getNodeInput(node: string, context: CaseContext, workflow: WorkflowState) {
  const common = { case_id: context.case_id, customer_id: context.customer_id, product: context.product }
  switch (node) {
    case 'EXISTING_CUSTOMER_GATE': return { ...common, existing_customer: context.existing_customer, relationship_months: context.relationship_months }
    case 'PRODUCT_AGENT': return { ...common, requested_amount: context.requested_amount, metadata: context.metadata }
    case 'DOCUMENT_COMPLETENESS': return { required_documents: context.required_documents, submitted_documents: context.submitted_documents }
    case 'ACCOUNT_TURNOVER': return { customer_id: context.customer_id, relationship_months: context.relationship_months, source: 'core_banking_mock' }
    case 'FINANCIAL_METRICS': return { annual_revenue: context.annual_revenue, pretax_profit_last_2_years: context.pretax_profit_last_2_years }
    case 'TAX_CONSISTENCY': return { annual_revenue: context.annual_revenue, tax_declared_revenue: context.tax_declared_revenue }
    case 'CREDIT_AGENT': return { requested_amount: context.requested_amount, cic_bad_debt: context.cic_bad_debt, upstream_artifacts: Object.keys(workflow.artifacts).filter((key) => ['FINANCIAL_METRICS', 'ACCOUNT_TURNOVER', 'TAX_CONSISTENCY'].includes(key)) }
    case 'COMPLIANCE_AGENT': return { kyc_aml_flags: context.kyc_aml_flags, rag_namespace: 'AML' }
    case 'READINESS_RULE_ENGINE': return { route: workflow.route, artifact_statuses: Object.fromEntries(Object.entries(workflow.artifacts).map(([key, value]) => [key, value.status])) }
    case 'MANDATORY_CRITIC': return { artifacts_to_review: Object.keys(workflow.artifacts).filter((key) => key !== 'MANDATORY_CRITIC'), max_rework: 1 }
    case 'CITATION_VALIDATOR': return { citation_ids: Object.keys(workflow.citation_results), checks: ['exact_quote', 'content_hash', 'authority', 'validity'] }
    case 'POLICY_GATE': return { critic_verdict: workflow.critic_verdict, citation_results: workflow.citation_results }
    default: return common
  }
}

function getNodeOutput(node: string, artifact: AgentArtifact | undefined, workflow: WorkflowState) {
  if (node === 'POLICY_GATE') return { final_status: workflow.final_status, critic_verdict: workflow.critic_verdict, handoff: 'HUMAN_REVIEW' }
  if (node === 'CITATION_VALIDATOR') return { validation_results: workflow.citation_results, artifact }
  return artifact ?? { status: 'PASS', summary: `${node} completed`, metrics: {}, warnings: [] }
}

function computeDurations(route: string[], totalMs = 12_000) {
  const weights = route.map((node) => getNodeKind(node) === 'ai' ? 1.65 : getNodeKind(node) === 'control' ? 1.15 : .85)
  const sum = weights.reduce((total, value) => total + value, 0)
  return weights.map((weight) => Math.round(totalMs * weight / sum))
}

const delay = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds))

export function WorkflowCanvas({ context, workflow }: { context: CaseContext; workflow: WorkflowState }) {
  const [runnerStatus, setRunnerStatus] = useState<RunnerStatus>('idle')
  const [activeIndex, setActiveIndex] = useState(-1)
  const [completedCount, setCompletedCount] = useState(0)
  const [selectedNode, setSelectedNode] = useState(workflow.route[0])
  const [elapsedMs, setElapsedMs] = useState(0)
  const [detailOpen, setDetailOpen] = useState(true)
  const runToken = useRef(0)
  const durations = useMemo(() => computeDurations(workflow.route), [workflow.route])

  useEffect(() => () => { runToken.current += 1 }, [])
  useEffect(() => {
    if (runnerStatus !== 'running') return
    const startedAt = performance.now() - elapsedMs
    const timer = window.setInterval(() => setElapsedMs(performance.now() - startedAt), 100)
    return () => window.clearInterval(timer)
  }, [runnerStatus])

  const runWorkflow = async () => {
    const token = ++runToken.current
    setRunnerStatus('running')
    setActiveIndex(0)
    setCompletedCount(0)
    setElapsedMs(0)
    for (let index = 0; index < workflow.route.length; index += 1) {
      if (token !== runToken.current) return
      setActiveIndex(index)
      setSelectedNode(workflow.route[index])
      setDetailOpen(true)
      await delay(durations[index])
      if (token !== runToken.current) return
      setCompletedCount(index + 1)
    }
    setActiveIndex(-1)
    setElapsedMs(durations.reduce((sum, value) => sum + value, 0))
    setRunnerStatus('completed')
  }

  const resetWorkflow = () => {
    runToken.current += 1
    setRunnerStatus('idle')
    setActiveIndex(-1)
    setCompletedCount(0)
    setElapsedMs(0)
  }

  const artifact = workflow.artifacts[selectedNode]
  const progress = workflow.route.length ? completedCount / workflow.route.length * 100 : 0

  return <section className="work-card workflow-studio">
    <div className="workflow-studio-header">
      <div className="workflow-heading"><div className="workflow-logo"><Route size={18} /></div><div><h2>Visual Hybrid-Agent Workflow</h2><p>Business rules và AI agents chạy tuần tự theo route của hồ sơ</p></div></div>
      <div className="runner-toolbar"><span className={`runner-state ${runnerStatus}`}><i />{runnerStatus === 'idle' ? 'Sẵn sàng' : runnerStatus === 'running' ? 'Đang thực thi' : 'Đã hoàn tất'}</span><span className="runner-time"><Timer size={13} />{(elapsedMs / 1000).toFixed(1)}s / 12.0s</span>{runnerStatus === 'completed' && <button className="runner-reset" onClick={resetWorkflow}><RefreshCw size={14} /> Reset</button>}<button className="runner-play" disabled={runnerStatus === 'running'} onClick={runWorkflow}>{runnerStatus === 'running' ? <LoaderCircle className="spin" size={15} /> : <Play size={15} fill="currentColor" />}{runnerStatus === 'completed' ? 'Chạy lại' : runnerStatus === 'running' ? 'Đang chạy...' : 'Chạy workflow'}</button></div>
    </div>
    <div className="runner-progress"><i style={{ width: `${progress}%` }} /></div>
    <div className="workflow-legend"><span><i className="business" /> Nghiệp vụ</span><span><i className="ai" /> AI / RAG</span><span><i className="control" /> Control & Safety</span><small>Click node để xem Input / Output</small></div>
    <div className="workflow-canvas-viewport">
      <div className="workflow-canvas-grid" />
      <div className="visual-pipeline">
        <div className={`terminal-node start ${runnerStatus !== 'idle' ? 'completed' : ''}`}><span><Zap size={15} /></span><strong>Case Intake</strong><small>Trigger</small></div>
        {workflow.route.map((node, index) => {
          const kind = getNodeKind(node)
          const isRunning = runnerStatus === 'running' && activeIndex === index
          const isCompleted = completedCount > index
          const isWaiting = runnerStatus === 'running' && activeIndex < index
          const NodeIcon = kind === 'ai' ? BrainCircuit : kind === 'control' ? ShieldCheck : GitBranch
          return <div className="pipeline-segment" key={node}>
            <div className={`workflow-edge ${isRunning || isCompleted ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}><span /><i /></div>
            <button onClick={() => { setSelectedNode(node); setDetailOpen(true) }} className={`visual-node ${kind} ${isRunning ? 'running' : ''} ${isCompleted ? 'completed' : ''} ${isWaiting ? 'waiting' : ''} ${selectedNode === node ? 'selected' : ''}`}>
              <i className="port input-port" />
              <div className="node-top"><span className="node-icon">{isRunning ? <LoaderCircle className="spin" size={16} /> : isCompleted ? <Check size={16} /> : <NodeIcon size={16} />}</span><span className="node-kind">{kind === 'ai' ? 'AI AGENT' : kind === 'control' ? 'CONTROL' : 'BUSINESS'}</span><ChevronRight size={13} /></div>
              <strong>{NODE_LABELS[node] ?? node}</strong>
              <small>{workflow.artifacts[node]?.engine ?? 'DETERMINISTIC'}</small>
              <div className="node-footer"><span>{isRunning ? 'Processing...' : isCompleted ? `${durations[index]} ms` : 'Waiting'}</span>{AI_NODES.has(node) && <Sparkles size={11} />}</div>
              <i className="port output-port" />
            </button>
          </div>
        })}
        <div className="pipeline-segment"><div className={`workflow-edge ${runnerStatus === 'completed' ? 'active completed' : ''}`}><span /><i /></div><div className={`terminal-node end ${runnerStatus === 'completed' ? 'completed' : ''}`}><span>{runnerStatus === 'completed' ? <Check size={15} /> : <CircleStop size={15} />}</span><strong>HITL Handoff</strong><small>{workflow.final_status}</small></div></div>
      </div>
    </div>
    <div className={`node-inspector ${detailOpen ? 'open' : ''}`}>
      <button className="inspector-toggle" onClick={() => setDetailOpen((current) => !current)}><div><Code2 size={15} /><span>Node inspector</span><strong>{NODE_LABELS[selectedNode] ?? selectedNode}</strong></div><ChevronDown size={16} /></button>
      {detailOpen && <div className="inspector-content">
        <div className="inspector-summary"><div className={`inspector-icon ${getNodeKind(selectedNode)}`}>{getNodeKind(selectedNode) === 'ai' ? <Bot size={19} /> : getNodeKind(selectedNode) === 'control' ? <ShieldCheck size={19} /> : <GitBranch size={19} />}</div><div><div><span>{getNodeKind(selectedNode).toUpperCase()}</span>{artifact && <ArtifactPill status={artifact.status} />}</div><h3>{NODE_LABELS[selectedNode] ?? selectedNode}</h3><p>{getNodeDescription(selectedNode)}</p></div></div>
        <div className="io-panel"><div className="io-heading"><FileJson size={14} /><strong>Input</strong><span>JSON</span></div><pre>{JSON.stringify(getNodeInput(selectedNode, context, workflow), null, 2)}</pre></div>
        <div className="io-arrow"><ChevronRight size={18} /></div>
        <div className="io-panel output"><div className="io-heading"><FileJson size={14} /><strong>Output</strong><span>JSON</span></div><pre>{JSON.stringify(getNodeOutput(selectedNode, artifact, workflow), null, 2)}</pre></div>
      </div>}
    </div>
  </section>
}
