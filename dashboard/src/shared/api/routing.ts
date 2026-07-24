import { apiRequest } from './client'

export type RoutingRule = {
  id: string
  project: string | null
  name: string
  priority: number
  match: Record<string, unknown>
  action: Record<string, unknown>
  enabled: boolean
  created_at: string
  updated_at: string
}

export type RoutingConfig = {
  lb_strategy: string
  ha_enabled: boolean
  min_health_score: number
  min_battery_percent: number
  rate_limit_per_minute: number
  rate_limit_per_hour: number
  rate_limit_per_day: number
  project_rate_limit_per_minute: number
  otp_queue_weight: number
  marketing_queue_weight: number
  marketing_jitter_max_seconds: number
  sim_daily_quota_default: number
  adaptive_throttle_enabled: boolean
  adaptive_failure_threshold: number
  updated_at: string
}

export async function listRoutingRules(token: string) {
  return apiRequest<{ results: RoutingRule[] }>('/routing-rules/', { token })
}

export async function createRoutingRule(
  token: string,
  body: {
    name: string
    priority?: number
    match?: Record<string, unknown>
    action?: Record<string, unknown>
    enabled?: boolean
    project?: string | null
  },
) {
  return apiRequest<RoutingRule>('/routing-rules/', {
    method: 'POST',
    token,
    body,
  })
}

export async function updateRoutingRule(
  token: string,
  id: string,
  body: Partial<RoutingRule>,
) {
  return apiRequest<RoutingRule>(`/routing-rules/${id}/`, {
    method: 'PATCH',
    token,
    body,
  })
}

export async function deleteRoutingRule(token: string, id: string) {
  return apiRequest<void>(`/routing-rules/${id}/`, {
    method: 'DELETE',
    token,
  })
}

export async function getRoutingConfig(token: string) {
  return apiRequest<RoutingConfig>('/routing/config/', { token })
}

export async function updateRoutingConfig(
  token: string,
  body: Partial<RoutingConfig>,
) {
  return apiRequest<RoutingConfig>('/routing/config/', {
    method: 'PATCH',
    token,
    body,
  })
}
