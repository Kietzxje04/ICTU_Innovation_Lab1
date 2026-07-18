import { useState } from 'react'
import { CircleHelp, FilePlus2, Gauge, History, Landmark, LogOut, Menu, Search, Settings, X } from 'lucide-react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useReadiness } from '../readiness-context'
import { useAuth } from '../auth-context'
import './ProfileMenu.css'

const navItems = [
  { to: '/', label: 'Bảng điều hành hồ sơ', icon: Gauge, end: true },
  { to: '/cases/new', label: 'Tạo hồ sơ', icon: FilePlus2 },
  { to: '/trace', label: 'Nhật ký thực thi', icon: History },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { dataMode } = useReadiness()
  const { user, logout } = useAuth()
  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }
  return <div className="app-shell">
    <aside className={`sidebar ${open ? 'is-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Landmark size={20} /></div><div><strong>NexusOps AI</strong><span>Đánh giá hồ sơ vay SME</span></div><button className="close-nav" onClick={() => setOpen(false)}><X /></button></div>
      <nav className="nav-list">{navItems.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)} className={({ isActive }) => isActive ? 'active' : ''}><Icon size={17} /><span>{label}</span></NavLink>)}</nav>
      <div className="nav-bottom"><a href="#settings"><Settings size={17} />Cài đặt</a><a href="#help"><CircleHelp size={17} />Trợ giúp</a></div>
    </aside>
    {open && <button className="nav-backdrop" onClick={() => setOpen(false)} />}
    <div className="app-main">
      <header className="topbar"><button className="menu-button" onClick={() => setOpen(true)}><Menu /></button><div className="topbar-title">NexusOps <span>Điều phối tác nhân</span></div><div className="global-search"><Search size={16} /><input aria-label="Tìm kiếm" value={new URLSearchParams(location.search).get('q') ?? ''} onChange={(event) => navigate(`/?q=${encodeURIComponent(event.target.value)}`)} placeholder="Tìm mã hồ sơ, khách hàng..." /></div><span className="mock-mode">{dataMode === 'api' ? 'DỮ LIỆU API' : 'LỖI API'}</span><div className="profile-menu"><div className="profile-card"><strong>{user?.full_name}</strong><span>{user?.role_name ?? user?.role_id}</span><button onClick={handleLogout}><LogOut size={13} /> Đăng xuất</button></div></div></header>
      {children}
    </div>
  </div>
}
