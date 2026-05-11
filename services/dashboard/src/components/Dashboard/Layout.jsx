import { Outlet, NavLink } from 'react-router-dom'

const NAV = [
  { to: '/map',       label: 'Live Map',   icon: '🗺️' },
  { to: '/farms',     label: 'My Farms',   icon: '🌾' },
  { to: '/analytics', label: 'Analytics',  icon: '📊' },
]

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">

      {/* ── Sidebar ── */}
      <aside className="w-56 bg-[#1a2414] text-white flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-white/10">
          <span className="text-lg font-semibold text-[#4a9261]">AgroSense</span>
          <p className="text-xs text-white/40 mt-0.5">Crop Monitoring</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-[#2d6a3f] text-white font-medium'
                    : 'text-white/60 hover:text-white hover:bg-white/5'
                }`
              }
            >
              <span className="text-base">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Version */}
        <div className="px-5 py-3 text-xs text-white/20 border-t border-white/10">
          AgroSense v1.0 · SMIU FYP
        </div>
      </aside>

      {/* ── Main content ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-shrink-0">
          <h1 className="text-sm font-medium text-gray-600">
            Satellite-Based Crop Monitoring — Pakistan
          </h1>
          <button
            onClick={() => {
              localStorage.removeItem('agrosense_token')
              window.location.href = '/login'
            }}
            className="text-xs text-gray-400 hover:text-gray-700 transition-colors"
          >
            Sign out
          </button>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto bg-[#f5f3ee]">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
