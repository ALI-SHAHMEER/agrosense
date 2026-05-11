import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout       from './components/Dashboard/Layout'
import MapPage      from './pages/MapPage'
import FarmsPage    from './pages/FarmsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import LoginPage    from './pages/LoginPage'

// Simple auth guard — replace with real JWT check in Phase 4
function PrivateRoute({ children }) {
  const token = localStorage.getItem('agrosense_token')
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route index           element={<Navigate to="/map" replace />} />
          <Route path="map"      element={<MapPage />} />
          <Route path="farms"    element={<FarmsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
