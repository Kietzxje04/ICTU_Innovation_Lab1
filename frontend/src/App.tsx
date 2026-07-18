import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { CaseDetailPage } from './pages/CaseDetailPage'
import { DashboardPage } from './pages/DashboardPage'
import { NewCasePage } from './pages/NewCasePage'
import { TracePage } from './pages/TracePage'
import { ReadinessProvider } from './readiness-context'

export default function App() {
  return <ReadinessProvider><Layout><Routes>
    <Route path="/" element={<DashboardPage />} />
    <Route path="/cases/new" element={<NewCasePage />} />
    <Route path="/cases/:caseId" element={<CaseDetailPage />} />
    <Route path="/trace" element={<TracePage />} />
    <Route path="*" element={<DashboardPage />} />
  </Routes></Layout></ReadinessProvider>
}
