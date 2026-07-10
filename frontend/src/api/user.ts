import request from './request'

export interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  phone: string | null
  avatar: string | null
  role: string
  is_active: boolean
  created_at: string
}

export interface UserCreate {
  username: string
  email: string
  password: string
  full_name?: string
  phone?: string
  role?: string
}

export interface UserQuery {
  page?: number
  size?: number
  keyword?: string
  role?: string
  is_active?: number
}

export const userApi = {
  getList: (params: UserQuery) =>
    request.get<null, { code: number; data: User[]; total: number; message: string }>(
      '/users/', { params }
    ),
  get: (id: number) => request.get(`/users/${id}`),
  create: (data: UserCreate) => request.post('/users/', data),
  update: (id: number, data: Partial<UserCreate> & { is_active?: boolean }) =>
    request.put(`/users/${id}`, data),
  remove: (id: number) => request.delete(`/users/${id}`),
}