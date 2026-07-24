import { apiRequest } from '../api/client'
import type { Device } from './devices'

export type AnalyticsOverview = {
  devices: {
    online: number
    offline: number
    busy: number
    pending: number
    total: number
  }
  messages: {
    sent_today: number
    failed_today: number
    sent_7d: number
    queue_depth: number
    inbound_today: number
  }
  series_7d: Array<{ day: string | null; sent: number }>
}

export type QueueSummary = {
  totals: {
    pending: number
    sending: number
    failed: number
    dead_letter: number
  }
  results: Array<{
    device_id: string
    name: string
    status: string
    pending: number
    sending: number
    failed: number
    dead_letter: number
  }>
}

export type DeviceEvent = {
  id: string
  type: string
  payload: Record<string, unknown>
  created_at: string
}

export type EventsPagination = {
  page: number
  page_size: number
  total: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export type DeviceCommand = {
  id: string
  action: string
  params: Record<string, unknown>
  status: string
  result: Record<string, unknown>
  created_at: string
}

export function fetchAnalyticsOverview(token: string) {
  return apiRequest<AnalyticsOverview>('/analytics/overview/', { token })
}

export function fetchQueuesSummary(token: string) {
  return apiRequest<QueueSummary>('/queues/summary/', { token })
}

export function fetchDevice(token: string, id: string) {
  return apiRequest<Device>(`/devices/${id}/`, { token })
}

export function fetchDeviceEvents(
  token: string,
  id: string,
  opts: { page?: number; pageSize?: number } = {},
) {
  const page = opts.page ?? 1
  const pageSize = opts.pageSize ?? 20
  const qs = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  return apiRequest<{ results: DeviceEvent[]; pagination: EventsPagination }>(
    `/devices/${id}/events/?${qs}`,
    { token },
  )
}

export function sendDeviceCommand(
  token: string,
  id: string,
  command: string,
  params: Record<string, unknown> = {},
) {
  return apiRequest<DeviceCommand>(`/devices/${id}/commands/`, {
    method: 'POST',
    token,
    body: { command, params },
  })
}

export function fetchDeviceCommand(token: string, deviceId: string, commandId: string) {
  return apiRequest<DeviceCommand>(`/devices/${deviceId}/commands/${commandId}/`, {
    token,
  })
}
