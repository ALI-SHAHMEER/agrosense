import { useEffect, useState } from 'react'
import { getFarms, getFields, fullAnalysis } from '../services/api'
import { Leaf, Droplets, TrendingUp, AlertTriangle, RefreshCw } from 'lucide-react'

function StatCard({ label, value, sub, color, icon: Icon }) {
  return (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
        </div>
        <div className={`p-2 rounded-lg bg-opacity-10 ${color.replace('text','bg')}`}>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
      </div>
    </div>
  )
}

function IndexBadge({ label, value, good, warn }) {
  const v = parseFloat(value)
  const color = v >= good ? 'bg-green-100 text-green-700'
              : v >= warn ? 'bg-yellow-100 text-yellow-700'
              : 'bg-red-100 text-red-700'
  return (
    <div className={`rounded-lg px-3 py-2 ${color}`}>
      <p className="text-xs font-medium">{label}</p>
      <p className="text-lg font-bold">{isNaN(v) ? '—' : v.toFixed(3)}</p>
    </div>
  )
}

export default function Dashboard() {
  const [farms, setFarms]       = useState([])
  const [fields, setFields]     = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [selectedField, setSelectedField] = useState('')

  useEffect(() => {
    getFarms().then(r => {
      setFarms(r.data)
      if (r.data.length > 0) {
        getFields(r.data[0].id).then(f => setFields(f.data))
      }
    })
  }, [])

  const runAnalysis = async () => {
    if (!selectedField) return
    setLoading(true)
    setError('')
    try {
      const res = await fullAnalysis(selectedField, {
        weather: { temp_celsius: 28, rainfall_mm: 10 },
        yield_params: { growing_days: 120, rainfall_mm: 200, temp_celsius: 26 },
      })
      setAnalysis(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Analysis failed. Run imagery analysis first.')
    } finally {
      setLoading(false)
    }
  }

  const stressColor = {
    Healthy:  'text-green-600',
    Stressed: 'text-yellow-600',
    Diseased: 'text-red-600',
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Crop intelligence overview</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Farms"  value={farms.length}  color="text-green-600"  icon={Leaf}          />
        <StatCard label="Total Fields" value={fields.length} color="text-blue-600"   icon={TrendingUp}    />
        <StatCard label="Analyses Run" value={analysis ? 1 : 0} color="text-purple-600" icon={RefreshCw} />
        <StatCard label="Alerts"
          value={analysis?.crop_stress?.prediction === 'Diseased' ? 1 : 0}
          color="text-red-600" icon={AlertTriangle}
        />
      </div>

      {/* Run analysis */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
        <h2 className="font-semibold text-gray-800 mb-4">Run Full Field Analysis</h2>
        <div className="flex gap-3">
          <select
            value={selectedField}
            onChange={e => setSelectedField(e.target.value)}
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          >
            <option value="">Select a field...</option>
            {fields.map(f => (
              <option key={f.id} value={f.id}>{f.name} — {f.crop_type}</option>
            ))}
          </select>
          <button
            onClick={runAnalysis}
            disabled={!selectedField || loading}
            className="bg-green-700 hover:bg-green-800 text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50 flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Analysing...' : 'Analyse'}
          </button>
        </div>
        {error && <p className="text-red-500 text-sm mt-3">{error}</p>}
      </div>

      {/* Analysis results */}
      {analysis && (
        <div className="space-y-4">
          {/* Indices */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="font-semibold text-gray-800 mb-4">Vegetation Indices</h2>
            <div className="grid grid-cols-4 gap-3">
              <IndexBadge label="NDVI" value={analysis.vegetation_indices.ndvi} good={0.5} warn={0.3} />
              <IndexBadge label="EVI"  value={analysis.vegetation_indices.evi}  good={0.4} warn={0.2} />
              <IndexBadge label="NDWI" value={analysis.vegetation_indices.ndwi} good={0.1} warn={-0.1} />
              <IndexBadge label="NDRE" value={analysis.vegetation_indices.ndre} good={0.3} warn={0.15} />
            </div>
          </div>

          {/* Model results grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Crop Stress */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-2 mb-3">
                <Leaf className="w-4 h-4 text-green-600" />
                <h3 className="font-semibold text-gray-700">Crop Health</h3>
              </div>
              <p className={`text-2xl font-bold ${stressColor[analysis.crop_stress.prediction]}`}>
                {analysis.crop_stress.prediction}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                Confidence: {(analysis.crop_stress.confidence * 100).toFixed(0)}%
              </p>
              <div className="mt-3 space-y-1">
                {Object.entries(analysis.crop_stress.probabilities).map(([cls, prob]) => (
                  <div key={cls} className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-16">{cls}</span>
                    <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                      <div
                        className="bg-green-500 h-1.5 rounded-full"
                        style={{ width: `${prob * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">{(prob * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Irrigation */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-2 mb-3">
                <Droplets className="w-4 h-4 text-blue-600" />
                <h3 className="font-semibold text-gray-700">Irrigation</h3>
              </div>
              <p className="text-2xl font-bold text-blue-600 capitalize">
                {analysis.irrigation.recommendation.replace(/_/g, ' ')}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                Soil moisture: {analysis.irrigation.soil_moisture_pct?.toFixed(1)}%
              </p>
              <p className="text-sm text-gray-500 mt-2">
                Recommended water: <strong>{analysis.irrigation.water_amount_mm} mm</strong>
              </p>
            </div>

            {/* Yield */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-purple-600" />
                <h3 className="font-semibold text-gray-700">Yield Prediction</h3>
              </div>
              <p className="text-2xl font-bold text-purple-600">
                {analysis.yield_prediction.predicted_yield_tha} t/ha
              </p>
              <p className="text-sm text-gray-400 mt-1">
                Range: {analysis.yield_prediction.yield_lower_bound} –{' '}
                {analysis.yield_prediction.yield_upper_bound} t/ha
              </p>
              <p className="text-sm text-gray-500 mt-2">
                Harvest readiness: <strong>{analysis.yield_prediction.harvest_readiness_pct}%</strong>
              </p>
            </div>

            {/* Soil */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <h3 className="font-semibold text-gray-700">Soil Assessment</h3>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">pH</span>
                  <span className="font-medium">{analysis.soil_assessment.soil_ph} — {analysis.soil_assessment.ph_status}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Salinity</span>
                  <span className="font-medium">{analysis.soil_assessment.salinity_ds_m} dS/m</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Organic Matter</span>
                  <span className="font-medium">{analysis.soil_assessment.organic_matter_pct}%</span>
                </div>
                <p className="text-xs text-amber-600 mt-2">{analysis.soil_assessment.organic_matter_status}</p>
              </div>
            </div>
          </div>

          {/* VRA */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <h3 className="font-semibold text-gray-700 mb-2">Variable Rate Application (VRA)</h3>
            <p className="text-lg font-bold text-green-700">
              Fertility Zone: {analysis.vra_zones.zone}
            </p>
            <p className="text-sm text-gray-600 mt-1">{analysis.vra_zones.fertiliser_recommendation}</p>
          </div>
        </div>
      )}
    </div>
  )
}
