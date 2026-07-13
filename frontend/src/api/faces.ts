import request from './request'

export interface Face {
  id: number
  user_id: number
  name: string
  employee_id: string | null
  image_url: string
  is_active: boolean
  created_at: string
}

export const faceApi = {
  getList: (params?: { page?: number; size?: number; user_id?: number }) =>
    request.get<null, { code: number; data: Face[]; total: number }>('/faces/', { params }),
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<null, { code: number; data: { url: string; filename: string } }>(
      '/faces/upload', formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  },
  create: (data: { user_id: number; name: string; employee_id?: string; image_url: string }) =>
    request.post('/faces/', data),
  remove: (id: number) => request.delete(`/faces/${id}`),
}