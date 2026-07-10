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

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export const authApi = {
  login: (username: string, password: string) =>
    request.post<null, { code: number; data: LoginResponse; message: string }>(
      '/auth/login',
      { username, password }
    ),

  register: (data: { username: string; email: string; password: string }) =>
    request.post('/auth/register', data),
}