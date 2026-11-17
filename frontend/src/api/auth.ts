import { api } from './client'

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserMe {
  id: number
  username: string
  email: string
  role: string
}

export const authApi = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const { data } = await api.post<LoginResponse>('/auth/login', {
      username,
      password,
    })
    return data
  },

  async me(): Promise<UserMe> {
    const { data } = await api.get<UserMe>('/auth/me')
    return data
  },
}