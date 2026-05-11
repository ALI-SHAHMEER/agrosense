import { useEffect, useState } from 'react'
import { getFarms, getFields, analyzeField, getHistory } from '../services/api'
import { Satellite, RefreshCw, Calendar } from 'lucide-react'

export default function Imagery() {
  const [farms, setFarms]     = useState([])
  const [fields, setFields]   = useState([])
  const [selectedFarm, setSelectedFarm]   = useState('')
  const [selectedField, setSelectedField] = useState('')
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate]     = useState('2024-03-01')
  const [cloudPct, setCloudPct]   = useState(30)
  const [loading, setLoading]     = useState(false)
  const [result, setResult]       = useState(null)
  const [history, setHistory]     = useState([])
  const [error, setError]         = useState('')

  useEffect(() => { getFarms().then(r => setFarms(r.data)) }, [])

  const onFarmChange = async (farmId) => {
    setSelectedFarm(farmId)
    setSelectedField('')
    setFields([])
    if (farmId) {
      const r = await getFields(farmId)
      setFields(r.data)
    }
  }

  const onFieldChange = async (fieldId) => {
    setSelectedField(fieldId)
    if (fieldId) {
      const r = await getHistory(fieldId)
      setHistory(r.data)
    }
  }

  const handleAnalyze = async () => {
    if (!selectedField) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const r = await analyzeField({
        field_id: selectedField,
        start_date: startDate,
        end_date: endDate,
        max_cloud_pct: cloudPct,
      })
      setResult(r.data)
      const h = await getHistory(selectedField)
      setHistory(h.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Satellite Imagery</h1>
        <p className="text-gray-500 text-sm mt-1">Fetch Sentinel-2 data and compute vegetation indices</p>
      </div>

      {/* Control panel */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
        <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <Satellite className="w-4 h-4 text-green-600" />
          Configure Analysis
        </h2>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Farm</label>
            <select
              value={selectedFarm}
              onChange={e => onFarmChange(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">Select farm...</option>
              {farms.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Field</label>
            <select
              value={selectedField}
              onChange={e => onFieldChange(e.target.value)}
              disabled={!selectedFarm}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
            >
              <option value="">Select field...</option>
              {fields.map(f => <option key={f.id} value={f.id}>{f.name} ({f.crop_type})</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Start Date</label>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">End Date</label>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Max cloud %:</label>
            <input type="number" value={cloudPct} onChange={e => setCloudPct(e.target.value)}
              min={0} max={100}
              className="w-20 border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
          </div>
          <button
            onClick={handleAnalyze}
            disabled={!selectedField || loading}
            className="flex items-center gap-2 bg-green-700 hover:bg-green-800 text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Fetching from GEE...' : 'Run Analysis'}
          </button>
        </div>
        {error && <p className="text-red-500 text-sm mt-3">{error}</p>}
      </div>

      {/* Result */}
      {result && result.status === 'success' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
          <h2 className="font-semibold text-gray-700 mb-4">Latest Results — {result.field_name}</h2>
          <p className="text-sm text-gray-500 mb-4">
            {result.images_found} Sentinel-2 images found · {result.date_range.start} to {result.date_range.end}
          </p>
          <div className="grid grid-cols-4 gap-3 mb-4">
            {Object.entries(result.indices).slice(0,4).map(([key, val]) => (
              <div key={key} className="bg-green-50 rounded-lg p-3">
                <p className="text-xs font-semibold text-green-700 uppercase">{key}</p>
                <p className="text-xl font-bold text-green-900">{val?.toFixed(3)}</p>
              </div>
            ))}
          </div>
          <div className="bg-amber-50 rounded-lg p-4">
            <p className="text-sm font-semibold text-amber-800">{result.interpretation.crop_health_status}</p>
            <p className="text-sm text-amber-600">{result.interpretation.moisture_status}</p>
          </div>
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-500" />
            Index History
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Date','NDVI','EVI','NDWI','NDRE','LAI'].map(h => (
                    <th key={h} className="text-left py-2 px-3 text-xs font-semibold text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {history.map(row => (
                  <tr key={row.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 px-3 text-gray-500 text-xs">
                      {new Date(row.calculated_at).toLocaleDateString()}
                    </td>
                    {['ndvi','evi','ndwi','ndre','lai'].map(k => (
                      <td key={k} className="py-2 px-3 font-mono text-xs">
                        {row[k]?.toFixed(3) ?? '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
