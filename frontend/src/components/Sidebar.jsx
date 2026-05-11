import { NavLink } from 'react-router-dom'
import { Leaf, LayoutDashboard, Map, Satellite, BarChart3, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/dashboard',  label: 'Dashboard',  icon: LayoutDashboard },
  { to: '/farms',      label: 'Farms',      icon: Map             },
  { to: '/imagery',    label: 'Imagery',    icon: Satellite       },
  { to: '/analytics',  label: 'Analytics',  icon: BarChart3       },
]

export default function Sidebar() {
  const { user, signOut } = useAuth()

  return (
    <aside className="w-56 bg-green-950 text-white flex flex-col h-screen fixed top-0 left-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-green-800">
        <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
          <Leaf className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="font-bold text-sm">AgroSense</p>
          <p className="text-green-400 text-xs">Crop Intelligence</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition
               ${isActive
                 ? 'bg-green-700 text-white font-medium'
                 : 'text-green-300 hover:bg-green-800 hover:text-white'}`
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User + logout */}
      <div className="px-4 py-4 border-t border-green-800">
        <p className="text-xs text-green-400 mb-1">Signed in as</p>
        <p className="text-sm font-medium truncate">{user?.name}</p>
        <p className="text-xs text-green-400 truncate mb-3">{user?.email}</p>
        <button
          onClick={signOut}
          className="flex items-center gap-2 text-xs text-green-400 hover:text-white transition"
        >
          <LogOut className="w-3.5 h-3.5" />
          Sign out
        </button>
      </div>
    </aside>
  )
}
