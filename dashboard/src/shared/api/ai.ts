import { apiRequest } from './client'

export type AnomalyFinding = {
  type: string
  explanation: string
  failure_rate?: number
  device_id?: string
  device_name?: string
}

export type RoutingSuggestion = {
  name: string
  priority: number
  match: Record<string, unknown>
  action: Record<string, unknown>
  confidence: number
  sample_size: number
  rationale: string
}

export function scanAnomalies(token: string, notify = true) {
  return apiRequest<{ results: AnomalyFinding[]; count: number }>(
    '/ai/anomalies/scan/',
    { method: notify ? 'POST' : 'GET', token },
  )
}

export function fetchRoutingSuggestions(token: string, hours = 24) {
  return apiRequest<{ results: RoutingSuggestion[] }>(
    `/ai/routing/suggestions/?hours=${hours}`,
    { token },
  )
}

export function fetchInboxDraft(token: string, conversationId: string) {
  return apiRequest<{ draft: string; source: string; note: string }>(
    `/ai/conversations/${conversationId}/draft/`,
    { method: 'POST', token },
  )
}

export function runDeviceAction(
  token: string,
  deviceId: string,
  capability: string,
  params?: Record<string, unknown>,
) {
  return apiRequest<{
    id: string
    action: string
    params: Record<string, unknown>
    status: string
    result: Record<string, unknown>
    created_at: string
  }>(`/devices/${deviceId}/actions/`, {
    method: 'POST',
    token,
    body: { capability, params: params || {} },
  })
}
