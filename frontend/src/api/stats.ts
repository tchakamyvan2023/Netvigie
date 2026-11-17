import { api } from './client'
import type { OverviewStats, TimeSeriesResponse } from '@/types'

export const statsApi = {
  async overview(): Promise<OverviewStats> {
    const { data } = await api.get<OverviewStats>('/stats/overview')
    return data
  },
  async timeseries(metric: string, period_minutes: number): Promise<TimeSeriesResponse> {
    const { data } = await api.get<TimeSeriesResponse>('/stats/timeseries', {
      params: { metric, period_minutes },
    })
    return data
  },
}