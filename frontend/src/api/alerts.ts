import request from './request'

export interface Alert {
  id: number
  alert_type: string
  level: 'info' | 'warning' | 'danger'
  status: 'pending' | 'handled' | 'ignored'
  description: string | null
  vehicle_id: string | null
  driver_name: string | null
  image_path: string | null
  handled_at: string | null
  created_at: string
  updated_at: string | null
}

export interface AlertListParams {
  page: number
  size: number
  alert_type?: string
  level?: 'info' | 'warning' | 'danger'
  status?: 'pending' | 'handled' | 'ignored'
  vehicle_id?: string
}

export function alertList(params: AlertListParams) {
  return request.get<unknown, { code: number; data: Alert[]; total: number; message: string }>(
    '/alerts/alerts', { params }
  )
}

export function alertHandle(id: number, status: 'handled' | 'ignored') {
  return request.patch<unknown, { code: number; data: Alert; message: string }>(
    `/alerts/alerts/${id}/handle`, { status }
  )
}