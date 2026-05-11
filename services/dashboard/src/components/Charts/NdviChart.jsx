import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

// Demo NDVI time-series — replaced by API data in Phase 4
const DEMO_DATA = [
  { month: 'Jan', ndvi: 0.42, evi: 0.35 },
  { month: 'Feb', ndvi: 0.51, evi: 0.44 },
  { month: 'Mar', ndvi: 0.65, evi: 0.58 },
  { month: 'Apr', ndvi: 0.72, evi: 0.64 },
  { month: 'May', ndvi: 0.68, evi: 0.61 },
  { month: 'Jun', ndvi: 0.55, evi: 0.49 },
  { month: 'Jul', ndvi: 0.38, evi: 0.33 },
  { month: 'Aug', ndvi: 0.44, evi: 0.39 },
  { month: 'Sep', ndvi: 0.61, evi: 0.54 },
  { month: 'Oct', ndvi: 0.70, evi: 0.63 },
  { month: 'Nov', ndvi: 0.66, evi: 0.58 },
  { month: 'Dec', ndvi: 0.48, evi: 0.42 },
]

export default function NdviChart({ data = DEMO_DATA }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="month" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
        <Tooltip
          contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #e5e7eb' }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          type="monotone" dataKey="ndvi" name="NDVI"
          stroke="#2d6a3f" strokeWidth={2} dot={false}
        />
        <Line
          type="monotone" dataKey="evi" name="EVI"
          stroke="#c9860a" strokeWidth={2} dot={false} strokeDasharray="4 2"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
