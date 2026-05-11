import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Attach token to every request
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// Auth
export const login    = (email, password) =>
  api.post('/auth/login', new URLSearchParams({ username: email, password }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
export const register = (data) => api.post('/auth/register', data)
export const getMe    = ()     => api.get('/auth/me')

// Farms
export const getFarms    = ()       => api.get('/farms/')
export const createFarm  = (data)   => api.post('/farms/', data)
export const deleteFarm  = (id)     => api.delete(`/farms/${id}`)

// Fields
export const getFields   = (farmId) => api.get(`/fields/farm/${farmId}`)
export const createField = (data)   => api.post('/fields/', data)
export const deleteField = (id)     => api.delete(`/fields/${id}`)

// Imagery
export const analyzeField = (data)  => api.post('/imagery/analyze', data)
export const getHistory   = (fieldId) => api.get(`/imagery/field/${fieldId}/history`)

// ML
export const fullAnalysis = (fieldId, data) =>
  api.post(`/ml/field/${fieldId}/full-analysis`, data)
export const getCropStress  = (fieldId) => api.post(`/ml/field/${fieldId}/crop-stress`)
export const getIrrigation  = (fieldId) => api.post(`/ml/field/${fieldId}/irrigation`)
export const getYield       = (fieldId) => api.post(`/ml/field/${fieldId}/yield`)
