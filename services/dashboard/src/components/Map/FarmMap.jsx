import { MapContainer, TileLayer, Polygon, Tooltip } from 'react-leaflet'

// Pakistan bounding centre
const DEFAULT_CENTER = [30.3753, 69.3451]
const DEFAULT_ZOOM   = 6

// Placeholder farm polygons — replaced by real API data in Phase 4
const DEMO_FARMS = [
  {
    id: 1,
    name: 'Farm Alpha — Punjab',
    status: 'healthy',
    ndvi: 0.72,
    coords: [[31.5, 72.3], [31.5, 72.5], [31.3, 72.5], [31.3, 72.3]],
  },
  {
    id: 2,
    name: 'Farm Beta — Sindh',
    status: 'stressed',
    ndvi: 0.38,
    coords: [[25.4, 68.4], [25.4, 68.6], [25.2, 68.6], [25.2, 68.4]],
  },
]

const STATUS_COLOR = {
  healthy:  '#2d6a3f',
  stressed: '#c9860a',
  diseased: '#dc2626',
}

export default function FarmMap() {
  return (
    <div className="w-full h-full min-h-[500px]">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: '100%', width: '100%' }}
      >
        {/* Base tile layer */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Farm polygons */}
        {DEMO_FARMS.map((farm) => (
          <Polygon
            key={farm.id}
            positions={farm.coords}
            pathOptions={{
              color:     STATUS_COLOR[farm.status] || '#888',
              fillColor: STATUS_COLOR[farm.status] || '#888',
              fillOpacity: 0.35,
              weight: 2,
            }}
          >
            <Tooltip>
              <div className="text-xs">
                <p className="font-semibold">{farm.name}</p>
                <p>Status: <span className="capitalize">{farm.status}</span></p>
                <p>NDVI: {farm.ndvi}</p>
              </div>
            </Tooltip>
          </Polygon>
        ))}
      </MapContainer>
    </div>
  )
}
