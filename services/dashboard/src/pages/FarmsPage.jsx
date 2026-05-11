const FARMS = [
  { id: 1, name: 'Farm Alpha',  crop: 'Wheat',        area: '12.4 ha', status: 'Healthy',  ndvi: 0.72, province: 'Punjab' },
  { id: 2, name: 'Farm Beta',   crop: 'Cotton',       area: '8.1 ha',  status: 'Stressed', ndvi: 0.38, province: 'Sindh'  },
]

const STATUS_STYLE = {
  Healthy:  'bg-green-100 text-green-800',
  Stressed: 'bg-amber-100 text-amber-800',
  Diseased: 'bg-red-100   text-red-800',
}

export default function FarmsPage() {
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-lg font-semibold text-[#1a2414]">My Farms</h1>
        <button className="text-sm bg-[#2d6a3f] text-white px-4 py-2 rounded-lg hover:bg-[#4a9261] transition-colors">
          + Add farm
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-left">
              {['Farm', 'Crop', 'Area', 'Province', 'NDVI', 'Status', ''].map(h => (
                <th key={h} className="px-4 py-3 font-medium text-gray-600 text-xs">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FARMS.map(farm => (
              <tr key={farm.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium text-[#1a2414]">{farm.name}</td>
                <td className="px-4 py-3 text-gray-600">{farm.crop}</td>
                <td className="px-4 py-3 text-gray-600">{farm.area}</td>
                <td className="px-4 py-3 text-gray-600">{farm.province}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-gray-200 rounded-full h-1.5">
                      <div
                        className="h-1.5 rounded-full bg-[#2d6a3f]"
                        style={{ width: `${farm.ndvi * 100}%` }}
                      />
                    </div>
                    <span className="text-gray-600">{farm.ndvi}</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_STYLE[farm.status]}`}>
                    {farm.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button className="text-xs text-[#2d6a3f] hover:underline">View</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
