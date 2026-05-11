import FarmMap from '../components/Map/FarmMap'

export default function MapPage() {
  return (
    <div className="flex flex-col h-full p-4 gap-4">

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Farms monitored',  value: '2',     unit: 'active' },
          { label: 'Avg NDVI',         value: '0.55',  unit: 'index' },
          { label: 'Stress alerts',    value: '1',     unit: 'fields' },
          { label: 'Last update',      value: '2h',    unit: 'ago' },
        ].map(({ label, value, unit }) => (
          <div key={label} className="bg-white rounded-xl p-4 border border-gray-200">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className="text-2xl font-semibold text-[#1a2414]">
              {value} <span className="text-sm font-normal text-gray-400">{unit}</span>
            </p>
          </div>
        ))}
      </div>

      {/* Map */}
      <div className="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden min-h-[400px]">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-medium text-gray-700">Farm Map — Pakistan</h2>
          <span className="text-xs text-gray-400">Demo data · Live data available in Phase 4</span>
        </div>
        <div className="h-[calc(100%-44px)]">
          <FarmMap />
        </div>
      </div>

    </div>
  )
}
