import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { CaseDetailPage } from './pages/CaseDetailPage'
import { DashboardPage } from './pages/DashboardPage'
import { NewCasePage } from './pages/NewCasePage'
import { TracePage } from './pages/TracePage'
import { CitationDetailPage, CitationLibraryPage } from './pages/CitationPages'
import { ReportPage } from './pages/ReportPage'
import { ReadinessProvider } from './readiness-context'
import { AuthProvider, useAuth } from './auth-context'
import { LoginPage } from './pages/LoginPage'
import { Navigate } from 'react-router-dom'

function ProtectedApp() {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <ReadinessProvider><Layout><Routes>
    <Route path="/" element={<DashboardPage />} />
    <Route path="/cases/new" element={<NewCasePage />} />
    <Route path="/cases/:caseId" element={<CaseDetailPage />} />
    <Route path="/trace" element={<TracePage />} />
    <Route path="/citations/:caseId" element={<CitationLibraryPage />} />
    <Route path="/citations/:caseId/:chunkId" element={<CitationDetailPage />} />
    <Route path="/reports/:caseId" element={<ReportPage />} />
    <Route path="*" element={<DashboardPage />} />
  </Routes></Layout></ReadinessProvider>
}

export default function App() {
  return <AuthProvider><Routes><Route path="/login" element={<LoginPage />} /><Route path="*" element={<ProtectedApp />} /></Routes></AuthProvider>
}
