import { api } from './client'
import type { Event, Page } from '@/types'

export const eventsApi = {
  async list(params: Record<string, unknown> = {}): Promise<Page<Event>> {
    const { data } = await api.get<Page<Event>>('/events', { params })
    return data
  },
}