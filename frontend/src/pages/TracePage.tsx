import { CheckCircle2, ChevronLeft, ChevronRight, Clock3, History } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { NODE_LABELS } from '../domain'
import { useReadiness } from '../readiness-context'
import { FinalStatusPill } from '../components/Status'

export function TracePage() {
  const { cases } = useReadiness()
  const [page, setPage] = useState(1)
  const pageSize = 5
  const pageCount = Math.max(1, Math.ceil(cases.length / pageSize))
  useEffect(() => { if (page > pageCount) setPage(pageCount) }, [page, pageCount])
  const visibleCases = cases.slice((page - 1) * pageSize, page * pageSize)
  return <main className="page trace-page">
    <div className="page-heading"><div><p className="eyebrow">GIÁM SÁT HỆ THỐNG</p><h1>Nhật ký thực thi</h1><p>Theo dõi kết quả và thời gian xử lý thực tế của từng khâu trong quy trình.</p></div></div>
    <div className="trace-cases">{visibleCases.map((item) => <section className="card trace-case" key={item.id}><div className="trace-case-header"><div><History size={18} /><div><Link to={`/cases/${item.id}`}>{item.company_name}</Link><span>{item.id} · {item.workflow.route.length} khâu</span></div></div><FinalStatusPill status={item.workflow.final_status} /></div><div className="trace-events">{item.workflow.trace.map((event) => <div key={event.node}><CheckCircle2 size={15} /><div><strong>{NODE_LABELS[event.node] ?? event.node}</strong><span>{event.message}</span></div><time><Clock3 size={11} /> {event.duration_ms} mili giây</time></div>)}</div></section>)}</div>
    {cases.length > 0 && <div className="readiness-pagination trace-pagination"><span>Hiển thị {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, cases.length)} / {cases.length} công ty</span><div><button disabled={page === 1} onClick={() => setPage((value) => value - 1)}><ChevronLeft size={14} /></button><strong>Trang {page} / {pageCount}</strong><button disabled={page === pageCount} onClick={() => setPage((value) => value + 1)}><ChevronRight size={14} /></button></div></div>}
  </main>
}
