import { api } from './client'
import type { Alert, Page } from '@/types'

export const alertsApi = {
  async list(params: Record<string, unknown> = {}): Promise<Page<Alert>> {
    const { data } = await api.get<Page<Alert>>('/alerts', { params })
    return data
  },
}