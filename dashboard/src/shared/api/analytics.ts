import { apiRequest } from './client'

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
    avg_latency_ms_today?: number | null
  }
  by_mode_today?: Record<string, number>
  series_7d: { day: string | null; sent: number }[]
}

export type OperatorStat = {
  operator: string
  sent: number
  avg_latency_ms: number | null
}

export type DeviceAnalytic = {
  device_id: string
  name: string
  status: string
  health_score: number
  sent: number
  failed: number
  avg_latency_ms: number | null
  lat?: number | null
  lng?: number | null
  city?: string | null
}

export type LatencyByMode = {
  mode: string
  avg_latency_ms: number | null
  count: number
}

export type MapPoint = {
  device_id: string
  name: string
  status: string
  health_score: number
  lat: number
  lng: number
  city: string
  accuracy_m?: number | null
  last_seen_at?: string | null
  location_received_at?: string | null
}

export function fetchAnalyticsOverview(token: string) {
  return apiRequest<AnalyticsOverview>('/analytics/overview/', { token })
}

export function fetchAnalyticsOperators(token: string, hours = 24) {
  return apiRequest<{ results: OperatorStat[] }>(
    `/analytics/operators/?hours=${hours}`,
    { token },
  )
}

export function fetchAnalyticsDevices(token: string, hours = 24) {
  return apiRequest<{ results: DeviceAnalytic[] }>(
    `/analytics/devices/?hours=${hours}`,
    { token },
  )
}

export function fetchAnalyticsLatency(token: string, hours = 24) {
  return apiRequest<{ by_mode: LatencyByMode[] }>(
    `/analytics/latency/?hours=${hours}`,
    { token },
  )
}

export function fetchAnalyticsTimeseries(
  token: string,
  metric = 'sent',
  hours = 24,
) {
  return apiRequest<{
    metric: string
    interval: string
    points: { t: string | null; v: number }[]
  }>(`/analytics/timeseries/?metric=${metric}&hours=${hours}`, { token })
}

export function fetchDeviceMap(token: string) {
  return apiRequest<{ results: MapPoint[] }>('/devices/map/', { token })
}
