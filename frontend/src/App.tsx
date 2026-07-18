import { useMemo, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle, ArrowLeft, Bell, BookOpen, Bot, Check, ChevronRight, CircleHelp, Clock3,
  Download, ExternalLink, FileCheck2, FileText, Gauge, History, Home, Landmark, LogOut,
  Menu, MessageSquareText, MoreHorizontal, PanelLeftClose, Search, Send, Settings, ShieldCheck,
  Sparkles, ThumbsDown, ThumbsUp, UserRound, X, Zap,
} from 'lucide-react'
import { companies, getCompany, type AgentState, type Company } from './data'

const navItems = [
  { to: '/', label: 'Trang chủ', icon: Home },
  { to: '/profiles/toan-cau', label: 'Hồ sơ', icon: FileText },
  { to: '/audit', label: 'Kiểm toán', icon: History },
]

function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const isProfile = location.pathname.startsWith('/profiles')

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? 'is-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><Landmark size={20} /></div>
          <div><strong>NexusOps AI</strong><span>Tín dụng SME</span></div>
          <button className="close-nav" onClick={() => setMobileOpen(false)} aria-label="Đóng menu"><X /></button>
        </div>
        <nav className="nav-list">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} onClick={() => setMobileOpen(false)} className={({ isActive }) => isActive || (label === 'Hồ sơ' && isProfile) ? 'active' : ''}>
              <Icon size={17} /><span>{label}</span>{label === 'Hồ sơ' && <span className="nav-count">4</span>}
            </NavLink>
          ))}
        </nav>
        <div className="nav-bottom">
          <a href="#settings"><Settings size={17} />Cài đặt</a>
          <a href="#help"><CircleHelp size={17} />Trợ giúp</a>
        </div>
      </aside>
      {mobileOpen && <button className="nav-backdrop" onClick={() => setMobileOpen(false)} />}
      <div className="app-main">
        <header className="topbar">
          <button className="menu-button" onClick={() => setMobileOpen(true)} aria-label="Mở menu"><Menu /></button>
          <div className="topbar-title">NexusOps <span>Credit Intelligence</span></div>
          <div className="global-search"><Search size={16} /><input aria-label="Tìm kiếm" placeholder="Tìm mã hồ sơ, khách hàng..." /></div>
          <div className="top-actions">
            <button aria-label="Thông báo"><Bell size={17} /><i /></button>
            <button aria-label="Trợ giúp"><CircleHelp size={17} /></button>
            <div className="avatar">QA</div>
            <button aria-label="Đăng xuất"><LogOut size={17} /></button>
          </div>
        </header>
        {children}
      </div>
    </div>
  )
}

function MetricCard({ label, value, note, icon: Icon, tone = 'blue' }: { label: string; value: string; note: string; icon: typeof Gauge; tone?: string }) {
  return <article className={`metric-card ${tone}`}>
    <div><span>{label}</span><strong>{value}</strong><small>{note}</small></div>
    <div className="metric-icon"><Icon size={22} /></div>
  </article>
}

function StatusBadge({ status }: { status: Company['status'] }) {
  const className = status === 'Chấp nhận' || status === 'Đã xác minh' ? 'success' : status === 'Từ chối' ? 'danger' : 'warning'
  return <span className={`status ${className}`}><i />{status}</span>
}

function HomePage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('Tất cả')
  const filtered = companies.filter((c) => {
    const matches = `${c.name} ${c.code}`.toLowerCase().includes(query.toLowerCase())
    return matches && (status === 'Tất cả' || c.status === status)
  })

  return <main className="page home-page">
    <div className="page-heading">
      <div><p className="eyebrow">AUDIT INTELLIGENCE</p><h1>Trang chủ Kiểm toán</h1><p>Tổng quan hoạt động và hiệu suất quyết định tín dụng.</p></div>
      <button className="secondary-button"><Download size={15} />Xuất báo cáo</button>
    </div>
    <section className="metrics-grid">
      <MetricCard label="Tổng lượt kiểm toán" value="12,450" note="↗ 4.2% so với tháng trước" icon={FileCheck2} />
      <MetricCard label="Tỷ lệ tuân thủ" value="98.5%" note="Mục tiêu tháng: 97%" icon={ShieldCheck} tone="green" />
      <MetricCard label="Vấn đề cần lưu ý" value="142" note="24 hồ sơ cần xử lý ngay" icon={AlertTriangle} tone="orange" />
      <MetricCard label="SLA trung bình" value="1h 48m" note="↓ 12 phút so với tuần trước" icon={Clock3} tone="purple" />
    </section>
    <section className="dashboard-grid">
      <article className="card audit-card">
        <div className="card-header responsive-header">
          <div><h2>Nhật ký Kiểm toán Gần đây</h2><p>Cập nhật theo thời gian thực từ hệ thống AI Agent</p></div>
          <Link to="/profiles/toan-cau">Xem tất cả <ChevronRight size={14} /></Link>
        </div>
        <div className="table-tools">
          <div className="inline-search"><Search size={15} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Tìm hồ sơ hoặc công ty" /></div>
          <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Lọc trạng thái">
            <option>Tất cả</option><option>Chấp nhận</option><option>Đã xác minh</option><option>Đang chờ rà soát</option><option>Từ chối</option>
          </select>
        </div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Thời gian</th><th>Mã hồ sơ</th><th>Khách hàng</th><th>Agent</th><th>Điểm AI</th><th>Trạng thái</th><th /></tr></thead>
            <tbody>{filtered.map((company) => <tr key={company.id} onClick={() => navigate(`/profiles/${company.id}`)}>
              <td>{company.submitted}</td><td className="code">{company.code}</td><td><strong>{company.shortName}</strong><span>{company.purpose}</span></td>
              <td>{company.agent}</td><td><span className="score">{company.score}%</span></td><td><StatusBadge status={company.status} /></td>
              <td><button aria-label={`Mở ${company.name}`}><ChevronRight size={17} /></button></td>
            </tr>)}</tbody>
          </table>
        </div>
        {filtered.length === 0 && <div className="empty-state">Không tìm thấy hồ sơ phù hợp.</div>}
        <div className="table-footer">Hiển thị {filtered.length} trên tổng số {companies.length} hồ sơ mẫu <span>Dữ liệu demo</span></div>
      </article>
      <aside className="side-stack">
        <article className="card chart-card">
          <div className="card-header"><div><h2>Độ chính xác AI</h2><p>7 ngày gần nhất</p></div><MoreHorizontal size={18} /></div>
          <div className="chart"><div className="chart-average">98.5% <span>Trung bình</span></div><div className="bars">
            {[68, 82, 75, 95, 61, 84, 91].map((h, i) => <div key={i}><i style={{ height: `${h}%` }} className={i === 4 ? 'orange-bar' : ''} /><span>{['T2','T3','T4','T5','T6','T7','CN'][i]}</span></div>)}
          </div></div>
        </article>
        <article className="card policy-card">
          <div className="card-header"><div><h2>Cập nhật Chính sách</h2><p>Tri thức mới nhất</p></div><BookOpen size={18} /></div>
          <div className="policy-item"><div><strong>SME Policy Manual v2.1</strong><span>Mới</span></div><p>Cập nhật tiêu chuẩn đánh giá rủi ro tín dụng cho SME năm 2024.</p><a href="#policy">Xem chi tiết <ExternalLink size={12} /></a></div>
          <div className="policy-item"><div><strong>Quy định Thẩm định Tài sản</strong></div><p>Bổ sung danh mục tài sản không đủ điều kiện thế chấp.</p><a href="#policy">Xem chi tiết <ExternalLink size={12} /></a></div>
          <button className="text-button">Mở Thư viện Chính sách</button>
        </article>
      </aside>
    </section>
  </main>
}

const stateLabels: Record<AgentState, string> = { done: 'Hoàn thành', running: 'Đang chạy', required: 'Bắt buộc', optional: 'Tùy chọn' }

function CompanySwitcher({ current }: { current: Company }) {
  const navigate = useNavigate()
  return <select className="company-switcher" value={current.id} onChange={(e) => navigate(`/profiles/${e.target.value}`)} aria-label="Chọn công ty">
    {companies.map((company) => <option key={company.id} value={company.id}>{company.shortName} · {company.code}</option>)}
  </select>
}

function ProfilePage() {
  const { companyId } = useParams()
  const company = getCompany(companyId)
  const navigate = useNavigate()
  const [chatOpen, setChatOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<string[]>([])
  const [decision, setDecision] = useState<'idle' | 'approved' | 'escalated'>('idle')
  const progress = Math.round(company.agents.reduce((sum, agent) => sum + agent.confidence, 0) / company.agents.length)
  const riskClass = company.risk === 'Cao' ? 'danger' : company.risk === 'Thấp' ? 'success' : 'warning'

  const sendMessage = () => {
    if (!message.trim()) return
    setMessages((prev) => [...prev, message.trim()])
    setMessage('')
  }

  return <main className="profile-page">
    <div className="profile-toolbar">
      <button className="back-button" onClick={() => navigate('/')}><ArrowLeft size={16} />Trang chủ</button>
      <div><span>Hồ sơ đang xử lý</span><CompanySwitcher current={company} /></div>
      <span className={`risk-badge ${riskClass}`}>Rủi ro {company.risk.toLowerCase()}</span>
    </div>
    <section className="company-hero">
      <div className="company-main"><span className="case-code">{company.code}</span><h1>{company.name}</h1><p><UserRound size={13} /> Người phụ trách: {company.owner}</p></div>
      <div className="verify-tag"><ShieldCheck size={14} /> Xác minh bằng chứng</div>
      <div className="amount"><strong>{company.amount}</strong><span>{company.purpose}</span></div>
      <div className="sla"><Clock3 size={15} />SLA: <strong>{company.sla}</strong></div>
    </section>
    <div className="profile-content">
      <div className="profile-primary">
        <section className="work-card agent-flow">
          <div className="section-title"><div><Sparkles size={17} /><h2>Quy trình Agent AI</h2></div><span>{progress}% hoàn tất</span></div>
          <div className="progress-line"><i style={{ width: `${progress}%` }} /></div>
          <div className="agent-steps">{company.agents.map((agent, index) => <div className={`agent-step ${agent.state}`} key={agent.name}>
            <div className="step-icon">{agent.state === 'done' ? <Check /> : agent.state === 'running' ? <Zap /> : <MoreHorizontal />}</div>
            <strong>{agent.name}</strong><span>{stateLabels[agent.state]}</span>{index < company.agents.length - 1 && <i className="connector" />}
          </div>)}</div>
        </section>
        {(company.objections.length > 0) && <section className="conflict-card">
          <div className="conflict-title"><AlertTriangle size={19} /><div><strong>Xung đột chưa giải quyết</strong><span>Cần cán bộ tín dụng xác nhận trước khi ra quyết định.</span></div></div>
          <div className="opinion-grid">
            <div className="opinion agree"><h3><ThumbsUp size={14} /> Sự đồng thuận ({company.consensus.length})</h3>{company.consensus.map((item) => <p key={item}>• {item}</p>)}</div>
            <div className="opinion object"><h3><ThumbsDown size={14} /> Phản đối ({company.objections.length})</h3>{company.objections.map((item) => <p key={item}>• {item}</p>)}</div>
          </div>
        </section>}
        <section className="work-card matrix-card">
          <div className="section-title"><div><Gauge size={17} /><h2>Ma trận Đánh giá</h2></div><span>4 tác vụ phân tích</span></div>
          <div className="matrix-grid">{company.agents.map((agent) => <article key={agent.name}>
            <div><strong>{agent.name}</strong><span>AI {agent.confidence}%</span></div>
            <div className="confidence"><i style={{ width: `${agent.confidence}%` }} /></div>
            <code>{agent.result}</code>
          </article>)}</div>
        </section>
      </div>
      <aside className="evidence-panel">
        <div className="section-title"><div><BookOpen size={17} /><h2>Bằng chứng & Chính sách</h2></div></div>
        <div className="citation"><p>“Mục 4.2: Thu nhập nước ngoài phải được kiểm toán đối chiếu với các tờ khai thuế được chứng nhận khi vượt quá 15% tổng doanh thu.”</p><span>Độ liên quan 96%</span></div>
        <label>Sổ tay nguồn</label><button className="document-button"><FileText size={15} />SME_Policy_Manual_v2.1 <ExternalLink size={13} /></button>
        <label>Ngày hiệu lực</label><strong className="effective-date">2023-10-15</strong>
        <button className="outline-button"><ExternalLink size={14} />Xem toàn bộ tài liệu chính sách</button>
        <div className="case-summary"><span>Kết quả AI</span><strong>{company.issue}</strong><small>Đề xuất: {company.recommendation}</small></div>
      </aside>
    </div>
    <footer className="decision-bar">
      <div><span>Kết quả cuối cùng</span><strong>{decision === 'idle' ? 'YÊU CẦU HÀNH ĐỘNG' : decision === 'approved' ? 'ĐÃ PHÊ DUYỆT' : 'ĐÃ CHUYỂN CẤP'}</strong></div>
      <div className="suggestion"><span>Hành động đề xuất</span><strong><Zap size={13} />{company.recommendation}</strong></div>
      <div className="decision-actions"><button onClick={() => setDecision('escalated')} className="outline-button">Từ chối / Chuyển cấp</button><button onClick={() => setDecision('approved')} className="primary-button"><Check size={15} />Phê duyệt hành động</button></div>
    </footer>
    <button className="chat-fab" onClick={() => setChatOpen(true)} aria-label="Mở hỗ trợ RAG AI"><MessageSquareText size={20} /></button>
    {chatOpen && <div className="chat-panel">
      <div className="chat-header"><div><Bot size={18} /><strong>Hỗ trợ RAG AI</strong><span>Trực tuyến</span></div><button onClick={() => setChatOpen(false)}><X size={17} /></button></div>
      <div className="chat-body"><div className="bot-message">Xin chào, tôi có thể giúp bạn tra cứu chính sách SME v2.1 hoặc giải thích hồ sơ <strong>{company.shortName}</strong>.</div>
        {messages.map((item, i) => <div className="user-message" key={`${item}-${i}`}>{item}</div>)}
      </div>
      <div className="chat-input"><input value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && sendMessage()} placeholder="Hỏi về hồ sơ hoặc chính sách..." /><button onClick={sendMessage}><Send size={17} /></button></div>
    </div>}
  </main>
}

function AuditPage() {
  const stats = useMemo(() => companies.map((c) => ({ ...c, compliance: Math.min(99, c.score + 5) })), [])
  return <main className="page simple-page"><div className="page-heading"><div><p className="eyebrow">KIỂM TOÁN HỆ THỐNG</p><h1>Lịch sử quyết định</h1><p>Truy vết đầy đủ các kết luận do AI Agent và cán bộ tín dụng thực hiện.</p></div></div>
    <section className="card audit-list"><div className="card-header"><div><h2>Nhật ký theo hồ sơ</h2><p>Dữ liệu minh họa được đồng bộ với trang chủ</p></div></div>
      {stats.map((company) => <Link to={`/profiles/${company.id}`} key={company.id} className="audit-row"><div className="audit-icon"><History size={17} /></div><div><strong>{company.code} · {company.shortName}</strong><span>{company.submitted} · {company.agent}</span></div><div><span>Tuân thủ</span><strong>{company.compliance}%</strong></div><StatusBadge status={company.status} /><ChevronRight size={17} /></Link>)}
    </section>
  </main>
}

function NotFound() {
  return <main className="page not-found"><FileText size={42} /><h1>Không tìm thấy trang</h1><p>Đường dẫn bạn truy cập không tồn tại.</p><Link className="primary-button" to="/">Về trang chủ</Link></main>
}

export default function App() {
  return <AppShell><Routes><Route path="/" element={<HomePage />} /><Route path="/profiles/:companyId" element={<ProfilePage />} /><Route path="/audit" element={<AuditPage />} /><Route path="*" element={<NotFound />} /></Routes></AppShell>
}
