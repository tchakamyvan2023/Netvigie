import { api } from './client'
import type { AgentNetvigie, AgentWazuh } from '@/types'

export const agentsApi = {
  async netvigie(): Promise<AgentNetvigie[]> {
    const { data } = await api.get<AgentNetvigie[]>('/agents')
    return data
  },
  async wazuh(): Promise<AgentWazuh[]> {
    const { data } = await api.get<AgentWazuh[]>('/agents/wazuh')
    return data
  },
}