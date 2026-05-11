import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Sidebar   from './components/Sidebar'
import Login     from './pages/Login'
import Register  from './pages/Register'
import Dashboard from './pages/Dashboard'
import Farms     from './pages/Farms'
import Imagery   from './pages/Imagery'
import Analytics from './pages/Analytics'

function PrivateLayout({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-green-700 font-medium animate-pulse">Loading AgroSense...</div>
    </div>
  )
  if (!user) return <Navigate to="/login" replace />
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 ml-56 p-8 max-w-5xl">
        {children}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login"    element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<PrivateLayout><Dashboard /></PrivateLayout>} />
          <Route path="/farms"     element={<PrivateLayout><Farms /></PrivateLayout>} />
          <Route path="/imagery"   element={<PrivateLayout><Imagery /></PrivateLayout>} />
          <Route path="/analytics" element={<PrivateLayout><Analytics /></PrivateLayout>} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
