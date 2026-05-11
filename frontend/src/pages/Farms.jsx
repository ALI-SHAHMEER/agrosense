import { useEffect, useState } from 'react'
import { getFarms, createFarm, deleteFarm, getFields, createField } from '../services/api'
import { Plus, Trash2, ChevronDown, ChevronRight, MapPin } from 'lucide-react'

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h3 className="font-semibold text-gray-800">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}

export default function Farms() {
  const [farms, setFarms]           = useState([])
  const [expanded, setExpanded]     = useState({})
  const [fieldMap, setFieldMap]     = useState({})
  const [showFarmModal, setShowFarmModal] = useState(false)
  const [showFieldModal, setShowFieldModal] = useState(null)
  const [farmForm, setFarmForm]     = useState({ name:'', district:'', province:'Sindh', area_ha:'', latitude:'', longitude:'' })
  const [fieldForm, setFieldForm]   = useState({ name:'', crop_type:'', area_ha:'' })
  const [saving, setSaving]         = useState(false)

  const load = () => getFarms().then(r => setFarms(r.data))
  useEffect(() => { load() }, [])

  const toggleFarm = async (id) => {
    setExpanded(e => ({ ...e, [id]: !e[id] }))
    if (!fieldMap[id]) {
      const r = await getFields(id)
      setFieldMap(m => ({ ...m, [id]: r.data }))
    }
  }

  const handleAddFarm = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await createFarm({
        ...farmForm,
        area_ha:   farmForm.area_ha   ? parseFloat(farmForm.area_ha)   : null,
        latitude:  farmForm.latitude  ? parseFloat(farmForm.latitude)  : null,
        longitude: farmForm.longitude ? parseFloat(farmForm.longitude) : null,
      })
      setShowFarmModal(false)
      setFarmForm({ name:'', district:'', province:'Sindh', area_ha:'', latitude:'', longitude:'' })
      load()
    } finally { setSaving(false) }
  }

  const handleAddField = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await createField({
        farm_id:  showFieldModal,
        name:     fieldForm.name,
        crop_type: fieldForm.crop_type,
        area_ha:  fieldForm.area_ha ? parseFloat(fieldForm.area_ha) : null,
      })
      const r = await getFields(showFieldModal)
      setFieldMap(m => ({ ...m, [showFieldModal]: r.data }))
      setShowFieldModal(null)
      setFieldForm({ name:'', crop_type:'', area_ha:'' })
    } finally { setSaving(false) }
  }

  const handleDeleteFarm = async (id) => {
    if (!confirm('Delete this farm and all its fields?')) return
    await deleteFarm(id)
    load()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Farms</h1>
          <p className="text-gray-500 text-sm mt-1">Manage your farms and fields</p>
        </div>
        <button
          onClick={() => setShowFarmModal(true)}
          className="flex items-center gap-2 bg-green-700 hover:bg-green-800 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
        >
          <Plus className="w-4 h-4" /> Add Farm
        </button>
      </div>

      {farms.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <MapPin className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No farms yet. Add your first farm.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {farms.map(farm => (
            <div key={farm.id} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              {/* Farm header */}
              <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
                onClick={() => toggleFarm(farm.id)}
              >
                <div className="flex items-center gap-3">
                  {expanded[farm.id]
                    ? <ChevronDown className="w-4 h-4 text-gray-400" />
                    : <ChevronRight className="w-4 h-4 text-gray-400" />
                  }
                  <div>
                    <p className="font-semibold text-gray-800">{farm.name}</p>
                    <p className="text-xs text-gray-400">
                      {[farm.district, farm.province].filter(Boolean).join(', ')}
                      {farm.area_ha ? ` · ${farm.area_ha} ha` : ''}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={e => { e.stopPropagation(); setShowFieldModal(farm.id) }}
                    className="text-xs bg-green-50 text-green-700 px-3 py-1 rounded-lg hover:bg-green-100 transition"
                  >
                    + Field
                  </button>
                  <button
                    onClick={e => { e.stopPropagation(); handleDeleteFarm(farm.id) }}
                    className="text-gray-400 hover:text-red-500 transition p-1"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Fields */}
              {expanded[farm.id] && (
                <div className="border-t border-gray-100 px-4 py-3 bg-gray-50">
                  {!fieldMap[farm.id] ? (
                    <p className="text-sm text-gray-400">Loading...</p>
                  ) : fieldMap[farm.id].length === 0 ? (
                    <p className="text-sm text-gray-400">No fields yet.</p>
                  ) : (
                    <div className="grid grid-cols-2 gap-2">
                      {fieldMap[farm.id].map(field => (
                        <div key={field.id} className="bg-white rounded-lg p-3 border border-gray-100">
                          <p className="font-medium text-sm text-gray-700">{field.name || 'Unnamed Field'}</p>
                          <p className="text-xs text-gray-400 mt-0.5">
                            {field.crop_type || 'No crop'}{field.area_ha ? ` · ${field.area_ha} ha` : ''}
                          </p>
                          <p className="text-xs text-gray-300 mt-1 font-mono truncate">{field.id}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add Farm Modal */}
      {showFarmModal && (
        <Modal title="Add Farm" onClose={() => setShowFarmModal(false)}>
          <form onSubmit={handleAddFarm} className="space-y-3">
            {[
              ['name',      'Farm Name',  'text',   'e.g. Sindh Farm 1'],
              ['district',  'District',   'text',   'e.g. Hyderabad'],
              ['province',  'Province',   'text',   'e.g. Sindh'],
              ['area_ha',   'Area (ha)',  'number', 'e.g. 50'],
              ['latitude',  'Latitude',  'number', 'e.g. 25.396'],
              ['longitude', 'Longitude', 'number', 'e.g. 68.374'],
            ].map(([key, label, type, placeholder]) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                <input
                  type={type}
                  step="any"
                  placeholder={placeholder}
                  value={farmForm[key]}
                  onChange={e => setFarmForm({...farmForm, [key]: e.target.value})}
                  required={key === 'name'}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={saving}
              className="w-full bg-green-700 text-white py-2 rounded-lg text-sm font-medium hover:bg-green-800 disabled:opacity-50 transition"
            >
              {saving ? 'Saving...' : 'Add Farm'}
            </button>
          </form>
        </Modal>
      )}

      {/* Add Field Modal */}
      {showFieldModal && (
        <Modal title="Add Field" onClose={() => setShowFieldModal(null)}>
          <form onSubmit={handleAddField} className="space-y-3">
            {[
              ['name',      'Field Name', 'text',   'e.g. Field A'],
              ['crop_type', 'Crop Type',  'text',   'e.g. wheat'],
              ['area_ha',   'Area (ha)',  'number', 'e.g. 10'],
            ].map(([key, label, type, placeholder]) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                <input
                  type={type}
                  step="any"
                  placeholder={placeholder}
                  value={fieldForm[key]}
                  onChange={e => setFieldForm({...fieldForm, [key]: e.target.value})}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={saving}
              className="w-full bg-green-700 text-white py-2 rounded-lg text-sm font-medium hover:bg-green-800 disabled:opacity-50 transition"
            >
              {saving ? 'Saving...' : 'Add Field'}
            </button>
          </form>
        </Modal>
      )}
    </div>
  )
}
