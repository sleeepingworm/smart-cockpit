import request from './request'

export interface Vehicle {
  id: number
  plate_number: string
  brand: string
  model: string
  color: string | null
  owner: string | null
  owner_phone: string | null
  status: number
  created_at: string
  updated_at: string | null
}

export interface VehicleCreate {
  plate_number: string
  brand: string
  model: string
  color?: string
  owner?: string
  owner_phone?: string
  status?: number
}

export interface VehicleQuery {
  page?: number
  size?: number
  keyword?: string
  status?: number
}

export const vehicleApi = {
  getList: (params: VehicleQuery) =>
    request.get<null, { code: number; data: Vehicle[]; total: number; message: string }>(
      '/vehicles/', { params }
    ),
  get: (id: number) =>
    request.get(`/vehicles/${id}`),
  create: (data: VehicleCreate) =>
    request.post('/vehicles/', data),
  update: (id: number, data: Partial<VehicleCreate>) =>
    request.put(`/vehicles/${id}`, data),
  remove: (id: number) =>
    request.delete(`/vehicles/${id}`),
}