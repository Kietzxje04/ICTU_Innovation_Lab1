import { useState } from 'react'
import { ArrowRight, Landmark, LockKeyhole, UserRound } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth-context'

export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [username, setUsername] = useState('employee-1')
  const [password, setPassword] = useState('NexusOps@2026')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setSubmitting(true); setError('')
    try { await login(username.trim(), password); navigate('/', { replace: true }) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Không thể đăng nhập') }
    finally { setSubmitting(false) }
  }
  return <main className="login-page"><section className="login-card"><div className="login-brand"><div className="brand-mark"><Landmark size={24} /></div><div><strong>NexusOps AI</strong><span>Đánh giá hồ sơ vay SME</span></div></div><div className="login-heading"><p className="eyebrow">ĐĂNG NHẬP HỆ THỐNG</p><h1>Chào mừng trở lại</h1><p>Đăng nhập để kiểm tra, chuyển cấp và phê duyệt hồ sơ theo thẩm quyền.</p></div><form onSubmit={submit}><label><span>Tên đăng nhập</span><div className="login-input"><UserRound size={16} /><input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></div></label><label><span>Mật khẩu</span><div className="login-input"><LockKeyhole size={16} /><input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" required /></div></label>{error && <div className="login-error">{error}</div>}<button className="primary-button login-submit" disabled={submitting}>{submitting ? 'Đang xác thực...' : 'Đăng nhập'} <ArrowRight size={15} /></button></form><div className="login-demo"><strong>Tài khoản mẫu</strong><span>Nhân viên: employee-1 · Quản lý: manager-1 · Giám đốc: director-1</span><small>Mật khẩu phát triển: NexusOps@2026</small></div></section></main>
}
