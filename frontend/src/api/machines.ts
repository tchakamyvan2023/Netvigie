import { api } from './client'
import type { Machine, Page } from '@/types'

export const machinesApi = {
  async list(params: Record<string, unknown> = {}): Promise<Page<Machine>> {
    const { data } = await api.get<Page<Machine>>('/machines', { params })
    return data
  },
  async get(id: number): Promise<Machine> {
    const { data } = await api.get<Machine>(`/machines/${id}`)
    return data
  },
  async metrics(id: number): Promise<unknown> {
    const { data } = await api.get(`/machines/${id}/metrics`)
    return data
  },
}