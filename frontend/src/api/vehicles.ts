import request from './request'

// TypeScript接口：定义Vehicle数据结构（和后端VehicleResp对应）
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
  color?: string          // 可选字段用 ? 或 | null
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

// 统一导出API对象，按模块分组
export const vehicleApi = {
  getList: (params: VehicleQuery) =>
    request.get<null, { code: number; data: Vehicle[]; total: number; message: string }>(
      '/vehicles/',
      { params }
    ),
  create: (data: VehicleCreate) =>
    request.post<null, { code: number; data: Vehicle; message: string }>('/vehicles/', data),
  update: (id: number, data: Partial<VehicleCreate>) =>
    request.put(`/vehicles/${id}`, data),
  remove: (id: number) =>
    request.delete(`/vehicles/${id}`),
}