import { api } from './client'
import type { Incident, Page } from '@/types'

export const incidentsApi = {
  async list(params: Record<string, unknown> = {}): Promise<Page<Incident>> {
    const { data } = await api.get<Page<Incident>>('/incidents', { params })
    return data
  },
  async get(id: number): Promise<Incident> {
    const { data } = await api.get<Incident>(`/incidents/${id}`)
    return data
  },
  async updateStatus(id: number, status: string, resolution_notes?: string): Promise<Incident> {
    const { data } = await api.patch<Incident>(`/incidents/${id}/status`, {
      status,
      resolution_notes,
    })
    return data
  },
}