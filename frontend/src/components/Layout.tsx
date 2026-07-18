import { useState } from 'react'
import { Bot, CircleHelp, FilePlus2, Gauge, History, Landmark, Menu, Search, Settings, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useReadiness } from '../readiness-context'

const navItems = [
  { to: '/', label: 'Readiness Dashboard', icon: Gauge, end: true },
  { to: '/cases/new', label: 'Tạo hồ sơ', icon: FilePlus2 },
  { to: '/trace', label: 'Execution Trace', icon: History },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const { dataMode } = useReadiness()
  return <div className="app-shell">
    <aside className={`sidebar ${open ? 'is-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Landmark size={20} /></div><div><strong>NexusOps AI</strong><span>SME Loan Readiness</span></div><button className="close-nav" onClick={() => setOpen(false)}><X /></button></div>
      <nav className="nav-list">{navItems.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)} className={({ isActive }) => isActive ? 'active' : ''}><Icon size={17} /><span>{label}</span></NavLink>)}</nav>
      <div className="agent-boundary"><Bot size={18} /><div><strong>Backend Agent runtime</strong><span>{dataMode === 'api' ? 'FastAPI workflow' : 'Backend chưa kết nối'} · Browser không gọi LLM trực tiếp</span></div></div>
      <div className="nav-bottom"><a href="#settings"><Settings size={17} />Cài đặt</a><a href="#help"><CircleHelp size={17} />Trợ giúp</a></div>
    </aside>
    {open && <button className="nav-backdrop" onClick={() => setOpen(false)} />}
    <div className="app-main">
      <header className="topbar"><button className="menu-button" onClick={() => setOpen(true)}><Menu /></button><div className="topbar-title">NexusOps <span>Hybrid-Agent Studio</span></div><div className="global-search"><Search size={16} /><input aria-label="Tìm kiếm" placeholder="Tìm mã hồ sơ, khách hàng..." /></div><span className="mock-mode">{dataMode === 'api' ? 'API DATA' : 'API ERROR'}</span><div className="avatar">QA</div></header>
      {children}
    </div>
  </div>
}
