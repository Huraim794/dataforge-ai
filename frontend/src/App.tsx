import { Routes, Route, Navigate } from 'react-router-dom'
import { isAuthenticated } from './services/api'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Jobs from './pages/Jobs'
import JobDetail from './pages/JobDetail'
import Proxies from './pages/Proxies'
import Schedules from './pages/Schedules'
import Targets from './pages/Targets'
import Extractions from './pages/Extractions'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Projects from './pages/Projects'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return <Layout>{children}</Layout>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/jobs" element={<ProtectedRoute><Jobs /></ProtectedRoute>} />
      <Route path="/jobs/:id" element={<ProtectedRoute><JobDetail /></ProtectedRoute>} />
      <Route path="/proxies" element={<ProtectedRoute><Proxies /></ProtectedRoute>} />
      <Route path="/schedules" element={<ProtectedRoute><Schedules /></ProtectedRoute>} />
      <Route path="/targets" element={<ProtectedRoute><Targets /></ProtectedRoute>} />
      <Route path="/extractions" element={<ProtectedRoute><Extractions /></ProtectedRoute>} />
      <Route path="/projects" element={<ProtectedRoute><Projects /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
