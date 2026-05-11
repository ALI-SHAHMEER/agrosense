import { useEffect, useState } from 'react'
import { getFarms, getFields, getHistory } from '../services/api'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, BarChart, Bar,
} from 'recharts'

export default function Analytics() {
  const [farms, setFarms]   = useState([])
  const [fields, setFields] = useState([])
  const [history, setHistory] = useState([])
  const [selectedFarm, setSelectedFarm]   = useState('')
  const [selectedField, setSelectedField] = useState('')

  useEffect(() => { getFarms().then(r => setFarms(r.data)) }, [])

  const onFarmChange = async (id) => {
    setSelectedFarm(id)
    setSelectedField('')
    setHistory([])
    if (id) { const r = await getFields(id); setFields(r.data) }
  }

  const onFieldChange = async (id) => {
    setSelectedField(id)
    if (id) {
      const r = await getHistory(id)
      setHistory(r.data.map(row => ({
        date: new Date(row.calculated_at).toLocaleDateString('en-PK', { month:'short', day:'numeric' }),
        NDVI: row.ndvi,
        EVI:  row.evi,
        NDWI: row.ndwi,
        NDRE: row.ndre,
        LAI:  row.lai,
      })).reverse())
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-500 text-sm mt-1">Vegetation index trends over time</p>
      </div>

      {/* Selectors */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-6 flex gap-4">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-600 mb-1">Farm</label>
          <select value={selectedFarm} onChange={e => onFarmChange(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500">
            <option value="">Select farm...</option>
            {farms.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-600 mb-1">Field</label>
          <select value={selectedField} onChange={e => onFieldChange(e.target.value)}
            disabled={!selectedFarm}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50">
            <option value="">Select field...</option>
            {fields.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
          </select>
        </div>
      </div>

      {history.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-400">Select a field to view index trends</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* NDVI + NDRE line chart */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="font-semibold text-gray-700 mb-4">Vegetation Health (NDVI & NDRE)</h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} domain={[-0.2, 1]} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="NDVI" stroke="#16a34a" strokeWidth={2} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="NDRE" stroke="#84cc16" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* NDWI + EVI */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="font-semibold text-gray-700 mb-4">Water Content & Enhanced Vegetation (NDWI & EVI)</h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="NDWI" stroke="#0284c7" strokeWidth={2} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="EVI"  stroke="#d97706" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* LAI bar chart */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="font-semibold text-gray-700 mb-4">Leaf Area Index (LAI)</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="LAI" fill="#16a34a" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
