import { CheckCircle2, Clock3, History } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NODE_LABELS } from '../domain'
import { useReadiness } from '../readiness-context'
import { FinalStatusPill } from '../components/Status'

export function TracePage() {
  const { cases } = useReadiness()
  return <main className="page trace-page"><div className="page-heading"><div><p className="eyebrow">OBSERVABILITY</p><h1>Execution Trace</h1><p>Nhật ký mock theo node; backend sau này sẽ thay bằng trace runtime thực tế.</p></div></div><div className="trace-cases">{cases.map((item) => <section className="card trace-case" key={item.id}><div className="trace-case-header"><div><History size={18} /><div><Link to={`/cases/${item.id}`}>{item.company_name}</Link><span>{item.id} · {item.workflow.route.length} nodes</span></div></div><FinalStatusPill status={item.workflow.final_status} /></div><div className="trace-events">{item.workflow.trace.map((event) => <div key={event.node}><CheckCircle2 size={15} /><div><strong>{NODE_LABELS[event.node] ?? event.node}</strong><span>{event.message}</span></div><time><Clock3 size={11} /> {event.duration_ms} ms</time></div>)}</div></section>)}</div></main>
}

