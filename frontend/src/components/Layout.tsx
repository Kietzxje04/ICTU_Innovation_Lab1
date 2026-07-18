import { useState } from 'react'
import { Bot, CircleHelp, FilePlus2, Gauge, History, Landmark, Menu, Search, Settings, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useReadiness } from '../readiness-context'
import { useAuth } from '../auth-context'

const navItems = [
  { to: '/', label: 'Bảng điều hành hồ sơ', icon: Gauge, end: true },
  { to: '/cases/new', label: 'Tạo hồ sơ', icon: FilePlus2 },
  { to: '/trace', label: 'Nhật ký thực thi', icon: History },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const { dataMode } = useReadiness()
  const { user, logout } = useAuth()
  return <div className="app-shell">
    <aside className={`sidebar ${open ? 'is-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Landmark size={20} /></div><div><strong>NexusOps AI</strong><span>Đánh giá hồ sơ vay SME</span></div><button className="close-nav" onClick={() => setOpen(false)}><X /></button></div>
      <nav className="nav-list">{navItems.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)} className={({ isActive }) => isActive ? 'active' : ''}><Icon size={17} /><span>{label}</span></NavLink>)}</nav>
      <div className="agent-boundary"><Bot size={18} /><div><strong>Bộ máy tác nhân phía máy chủ</strong><span>{dataMode === 'api' ? 'Quy trình FastAPI' : 'Máy chủ chưa kết nối'} · Trình duyệt không gọi mô hình ngôn ngữ trực tiếp</span></div></div>
      {user && <div className="sidebar-user"><strong>{user.full_name}</strong><span>{user.role_name ?? user.role_id}</span><button onClick={logout}>Đăng xuất</button></div>}
      <div className="nav-bottom"><a href="#settings"><Settings size={17} />Cài đặt</a><a href="#help"><CircleHelp size={17} />Trợ giúp</a></div>
    </aside>
    {open && <button className="nav-backdrop" onClick={() => setOpen(false)} />}
    <div className="app-main">
      <header className="topbar"><button className="menu-button" onClick={() => setOpen(true)}><Menu /></button><div className="topbar-title">NexusOps <span>Điều phối tác nhân</span></div><div className="global-search"><Search size={16} /><input aria-label="Tìm kiếm" placeholder="Tìm mã hồ sơ, khách hàng..." /></div><span className="mock-mode">{dataMode === 'api' ? 'DỮ LIỆU API' : 'LỖI API'}</span><div className="avatar">QA</div></header>
      {children}
    </div>
  </div>
}
