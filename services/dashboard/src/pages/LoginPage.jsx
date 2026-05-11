import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleLogin(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      if (res.ok) {
        const data = await res.json()
        localStorage.setItem('agrosense_token', data.access_token)
        navigate('/map')
      } else {
        setError('Invalid email or password')
      }
    } catch {
      // Dev bypass when API is not yet running
      if (email === 'demo@agrosense.pk' && password === 'demo') {
        localStorage.setItem('agrosense_token', 'demo-token')
        navigate('/map')
      } else {
        setError('Cannot reach API. Use demo@agrosense.pk / demo to preview UI.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f5f3ee]">
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-[#1a2414]">AgroSense</h1>
          <p className="text-sm text-gray-500 mt-1">Satellite Crop Monitoring · Pakistan</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl border border-gray-200 p-8">
          <h2 className="text-base font-semibold text-gray-800 mb-6">Sign in</h2>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg px-3 py-2 mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Email</label>
              <input
                type="email" required
                value={email} onChange={e => setEmail(e.target.value)}
                placeholder="you@agrosense.pk"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a3f] focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Password</label>
              <input
                type="password" required
                value={password} onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a3f] focus:border-transparent"
              />
            </div>

            <button
              type="submit" disabled={loading}
              className="w-full bg-[#2d6a3f] text-white py-2.5 rounded-lg text-sm font-medium hover:bg-[#4a9261] transition-colors disabled:opacity-60"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="text-xs text-gray-400 text-center mt-4">
            Demo: demo@agrosense.pk / demo
          </p>
        </div>

      </div>
    </div>
  )
}
