import NdviChart from '../components/Charts/NdviChart'

export default function AnalyticsPage() {
  return (
    <div className="p-6 space-y-5">
      <h1 className="text-lg font-semibold text-[#1a2414]">Analytics</h1>

      {/* NDVI trend */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-sm font-medium text-gray-700 mb-4">NDVI & EVI — Monthly Trend</h2>
        <NdviChart />
      </div>

      {/* Prediction summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { title: 'Yield Forecast',      value: '3.2 t/ha',   sub: 'Estimated harvest: Dec 2025',   color: 'border-green-400' },
          { title: 'Irrigation Status',   value: 'Hold',        sub: 'Soil moisture 64% — adequate',  color: 'border-amber-400' },
          { title: 'Soil Health Score',   value: '74 / 100',    sub: 'pH 6.8 · Org. matter 2.1%',    color: 'border-blue-400'  },
        ].map(({ title, value, sub, color }) => (
          <div key={title} className={`bg-white rounded-xl border-l-4 ${color} border border-gray-200 p-4`}>
            <p className="text-xs text-gray-500 mb-1">{title}</p>
            <p className="text-xl font-semibold text-[#1a2414]">{value}</p>
            <p className="text-xs text-gray-400 mt-1">{sub}</p>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-400 text-center pt-2">
        Demo data — live ML predictions connect in Phase 5
      </p>
    </div>
  )
}
