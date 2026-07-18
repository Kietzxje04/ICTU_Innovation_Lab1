import { AlertTriangle, ArrowRight, Bot, CheckCircle2, Clock3, FileSearch, Search, ShieldCheck } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRITIC_LABELS, type FinalStatus, type ProductType } from '../domain'
import { useReadiness } from '../readiness-context'
import { FinalStatusPill, ProductPill } from '../components/Status'

function Metric({ label, value, note, icon: Icon, tone }: { label: string; value: string; note: string; icon: typeof Bot; tone: string }) {
  return <article className={`readiness-metric ${tone}`}><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div><i><Icon size={21} /></i></article>
}

export function DashboardPage() {
  const { cases, dataMode, isLoading, error, refresh } = useReadiness()
  const [query, setQuery] = useState('')
  const [product, setProduct] = useState<'ALL' | ProductType>('ALL')
  const [status, setStatus] = useState<'ALL' | FinalStatus>('ALL')
  const filtered = useMemo(() => cases.filter((item) => {
    const text = `${item.id} ${item.company_name} ${item.context.customer_id}`.toLowerCase()
    return text.includes(query.toLowerCase()) && (product === 'ALL' || item.context.product === product) && (status === 'ALL' || item.workflow.final_status === status)
  }), [cases, product, query, status])
  const ready = cases.filter((item) => item.workflow.final_status === 'READY_FOR_HUMAN_REVIEW').length
  const evidence = cases.filter((item) => item.workflow.final_status === 'NEEDS_MORE_EVIDENCE').length
  const criticPass = cases.filter((item) => item.workflow.critic_verdict === 'PASS').length

  return <main className="page readiness-dashboard">
    {(isLoading || error) && <div className="safety-banner"><ShieldCheck size={18} /><div><strong>{isLoading ? 'Đang tải dữ liệu backend...' : 'Đang dùng dữ liệu fallback'}</strong><span>{error ?? 'Vui lòng chờ Agent workflow snapshots được tải.'}</span></div>{error && <button className="outline-button" onClick={refresh}>Kết nối lại</button>}</div>}
    <div className="page-heading"><div><p className="eyebrow">NEXUSOPS AI V3.1</p><h1>Bảng điều hành mức độ sẵn sàng hồ sơ vay</h1><p>Theo dõi mức độ sẵn sàng, bằng chứng và các điểm cần chuyên viên tham gia xử lý.</p></div><Link className="primary-button" to="/cases/new">Tạo hồ sơ mới <ArrowRight size={15} /></Link></div>
    <section className="readiness-metrics">
      <Metric label="Tổng hồ sơ" value={String(cases.length)} note="Hai quy trình dành cho SME" icon={FileSearch} tone="blue" />
      <Metric label="Sẵn sàng chuyển chuyên viên" value={String(ready)} note="Không phải quyết định tín dụng" icon={CheckCircle2} tone="green" />
      <Metric label="Thiếu bằng chứng" value={String(evidence)} note="Cần bổ sung hoặc xác minh" icon={AlertTriangle} tone="orange" />
      <Metric label="Phản biện đạt" value={`${criticPass}/${cases.length}`} note="Khâu phản biện bắt buộc đã chạy" icon={ShieldCheck} tone="purple" />
    </section>
    <section className="card readiness-list">
      <div className="card-header"><div><h2>Hàng đợi hồ sơ</h2><p>Dữ liệu {dataMode === 'api' ? 'từ máy chủ FastAPI' : 'chưa sẵn sàng'} theo thông tin hồ sơ và trạng thái quy trình</p></div><span className="live-indicator"><i /> Ảnh chụp trạng thái quy trình</span></div>
      <div className="readiness-filters"><label><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Mã hồ sơ, khách hàng..." /></label><select value={product} onChange={(event) => setProduct(event.target.value as typeof product)}><option value="ALL">Tất cả sản phẩm</option><option value="CORPORATE_OVERDRAFT">Thấu chi doanh nghiệp</option><option value="WORKING_CAPITAL">Vốn lưu động</option></select><select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}><option value="ALL">Tất cả trạng thái</option><option value="READY_FOR_HUMAN_REVIEW">Sẵn sàng rà soát</option><option value="NEEDS_MORE_EVIDENCE">Cần thêm bằng chứng</option><option value="BLOCKED">Bị chặn</option></select></div>
      <div className="table-scroll"><table className="readiness-table"><thead><tr><th>Hồ sơ / Khách hàng</th><th>Sản phẩm</th><th>Giá trị đề nghị</th><th>Quy trình</th><th>Phản biện</th><th>Trạng thái</th><th>SLA xử lý gần nhất</th><th /></tr></thead><tbody>{filtered.map((item) => <tr key={item.id}><td><strong>{item.company_name}</strong><span>{item.id} · {item.context.customer_id}</span></td><td><ProductPill product={item.context.product} /></td><td><strong>{new Intl.NumberFormat('vi-VN').format(item.context.requested_amount)} ₫</strong><span>{item.context.metadata.industry}</span></td><td><strong>{item.workflow.route.length} khâu</strong><span>{item.workflow.artifacts.DOCUMENT_COMPLETENESS?.metrics.completeness_ratio ? `${Math.round(item.workflow.artifacts.DOCUMENT_COMPLETENESS.metrics.completeness_ratio * 100)}% tài liệu` : 'Chờ phân tích'}</span></td><td><strong>{CRITIC_LABELS[item.workflow.critic_verdict]}</strong><span>Bắt buộc</span></td><td><FinalStatusPill status={item.workflow.final_status} /></td><td><strong><Clock3 size={12} /> {item.sla_due}</strong><span>Lần chạy gần nhất</span></td><td><Link className="row-open" to={`/cases/${item.id}`}><ArrowRight size={16} /></Link></td></tr>)}</tbody></table></div>
      {!filtered.length && <div className="empty-state">Không có hồ sơ phù hợp bộ lọc.</div>}
    </section>
  </main>
}
