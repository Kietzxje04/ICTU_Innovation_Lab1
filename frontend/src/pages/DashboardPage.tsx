import { AlertTriangle, ArrowRight, Bot, CheckCircle2, ChevronLeft, ChevronRight, Clock3, FileSearch, Search, ShieldCheck, Send } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CRITIC_LABELS, type FinalStatus, type ProductType } from '../domain'
import { useReadiness } from '../readiness-context'
import { FinalStatusPill, ProductPill } from '../components/Status'
import { useAuth } from '../auth-context'

function Metric({ label, value, note, icon: Icon, tone }: { label: string; value: string; note: string; icon: typeof Bot; tone: string }) {
  return <article className={`readiness-metric ${tone}`}><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div><i><Icon size={21} /></i></article>
}

export function DashboardPage() {
  const { cases, dataMode, isLoading, error, refresh } = useReadiness()
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState(params.get('q') ?? '')
  const [product, setProduct] = useState<'ALL' | ProductType>('ALL')
  const [status, setStatus] = useState<'ALL' | FinalStatus>('ALL')
  const [page, setPage] = useState(1)

  const todoCases = useMemo(() => {
    if (!user) return []
    const ROLE_ORDER: Record<string, number> = {
      EMPLOYEE: 0,
      MANAGER: 1,
      DIRECTOR: 2,
    }
    const userOrder = ROLE_ORDER[user.role_id] ?? -1
    return cases
      .filter((item) => {
        if (item.approval_status === 'APPROVED') return false
        if (item.workflow.final_status !== 'READY_FOR_HUMAN_REVIEW') return false
        const currentOrder = item.current_role ? (ROLE_ORDER[item.current_role] ?? 0) : 0
        return userOrder >= currentOrder
      })
      .sort((a, b) => {
        const aTrans = a.approval_status === 'TRANSFERRED' ? 1 : 0
        const bTrans = b.approval_status === 'TRANSFERRED' ? 1 : 0
        return bTrans - aTrans
      })
  }, [cases, user])

  useEffect(() => { setQuery(params.get('q') ?? ''); setPage(1) }, [params])
  const filtered = useMemo(() => cases.filter((item) => {
    const text = `${item.id} ${item.company_name} ${item.context.customer_id}`.toLowerCase()
    return text.includes(query.toLowerCase()) && (product === 'ALL' || item.context.product === product) && (status === 'ALL' || item.workflow.final_status === status)
  }), [cases, product, query, status])
  const pageSize = 10
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize))
  const visibleCases = filtered.slice((page - 1) * pageSize, page * pageSize)
  const updateQuery = (value: string) => { setQuery(value); setParams(value ? { q: value } : {}); setPage(1) }
  const ready = cases.filter((item) => item.workflow.final_status === 'READY_FOR_HUMAN_REVIEW').length
  const evidence = cases.filter((item) => item.workflow.final_status === 'NEEDS_MORE_EVIDENCE').length
  const criticPass = cases.filter((item) => item.workflow.critic_verdict === 'PASS').length
  return <main className="page readiness-dashboard">
    {(isLoading || error) && <div className="safety-banner"><ShieldCheck size={18} /><div><strong>{isLoading ? 'Đang tải dữ liệu backend...' : 'Đang dùng dữ liệu fallback'}</strong><span>{error ?? 'Vui lòng chờ dữ liệu được tải.'}</span></div>{error && <button className="outline-button" onClick={refresh}>Kết nối lại</button>}</div>}
    <div className="page-heading"><div><p className="eyebrow">NEXUSOPS AI V3.1</p><h1>Bảng điều hành hồ sơ vay</h1><p>Theo dõi mức độ sẵn sàng và trạng thái xử lý hồ sơ.</p></div><Link className="primary-button" to="/cases/new">Tạo hồ sơ mới <ArrowRight size={15} /></Link></div>
    <section className="readiness-metrics"><Metric label="Tổng hồ sơ" value={String(cases.length)} note="Hồ sơ dành cho SME" icon={FileSearch} tone="blue" /><Metric label="Sẵn sàng rà soát" value={String(ready)} note="Chờ chuyên viên xử lý" icon={CheckCircle2} tone="green" /><Metric label="Thiếu bằng chứng" value={String(evidence)} note="Cần bổ sung hoặc xác minh" icon={AlertTriangle} tone="orange" /><Metric label="Phản biện đạt" value={`${criticPass}/${cases.length}`} note="Khâu phản biện bắt buộc" icon={ShieldCheck} tone="purple" /></section>
    <section className="card readiness-list">
      <div className="card-header"><div><h2>Danh sách doanh nghiệp</h2><p>Dữ liệu {dataMode === 'api' ? 'từ máy chủ FastAPI' : 'chưa sẵn sàng'} theo hồ sơ và trạng thái.</p></div><span className="live-indicator"><i /> Cập nhật gần nhất</span></div>
      <div className="readiness-filters"><label><Search size={15} /><input value={query} onChange={(event) => updateQuery(event.target.value)} placeholder="Mã hồ sơ, khách hàng..." /></label><select value={product} onChange={(event) => { setProduct(event.target.value as typeof product); setPage(1) }}><option value="ALL">Tất cả sản phẩm</option><option value="CORPORATE_OVERDRAFT">Thấu chi doanh nghiệp</option><option value="WORKING_CAPITAL">Vốn lưu động</option></select><select value={status} onChange={(event) => { setStatus(event.target.value as typeof status); setPage(1) }}><option value="ALL">Tất cả trạng thái</option><option value="READY_FOR_HUMAN_REVIEW">Sẵn sàng rà soát</option><option value="NEEDS_MORE_EVIDENCE">Cần thêm bằng chứng</option><option value="BLOCKED">Bị chặn</option></select></div>
      <div className="table-scroll"><table className="readiness-table"><thead><tr><th>Hồ sơ / Khách hàng</th><th>Sản phẩm</th><th>Giá trị đề nghị</th><th>Quy trình</th><th>Phản biện</th><th>Trạng thái</th><th>SLA gần nhất</th><th /></tr></thead><tbody>{visibleCases.map((item) => <tr key={item.id}><td><strong>{item.company_name}</strong><span>{item.id} · {item.context.customer_id}</span></td><td><ProductPill product={item.context.product} /></td><td><strong>{new Intl.NumberFormat('vi-VN').format(item.context.requested_amount)} ₫</strong><span>{item.context.metadata.industry}</span></td><td><strong>{item.workflow.route.length} khâu</strong><span>{item.workflow.artifacts.DOCUMENT_COMPLETENESS?.metrics.completeness_ratio ? `${Math.round(item.workflow.artifacts.DOCUMENT_COMPLETENESS.metrics.completeness_ratio * 100)}% tài liệu` : 'Chờ phân tích'}</span></td><td><strong>{CRITIC_LABELS[item.workflow.critic_verdict]}</strong><span>Bắt buộc</span></td><td><FinalStatusPill status={item.workflow.final_status} /></td><td><strong><Clock3 size={12} /> {item.sla_due}</strong><span>Lần chạy gần nhất</span></td><td><Link className="row-open" to={`/cases/${item.id}`}><ArrowRight size={16} /></Link></td></tr>)}</tbody></table></div>
      {filtered.length > 0 && <div className="readiness-pagination"><span>Hiển thị {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, filtered.length)} / {filtered.length} doanh nghiệp</span><div><button disabled={page === 1} onClick={() => setPage((value) => value - 1)}><ChevronLeft size={14} /></button><strong>Trang {page} / {pageCount}</strong><button disabled={page === pageCount} onClick={() => setPage((value) => value + 1)}><ChevronRight size={14} /></button></div></div>}
      {!filtered.length && <div className="empty-state">Không có hồ sơ phù hợp bộ lọc.</div>}
    </section>
  </main>
}
