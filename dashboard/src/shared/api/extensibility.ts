import { apiRequest } from './client'

export type PluginInfo = {
  id: string
  name: string
  version: string
  hooks: string[]
  config_schema: Record<string, unknown>
  plugin_api: string
  installed: boolean
  enabled: boolean | null
  config: Record<string, unknown>
}

export type NotificationChannel = {
  id: string
  channel_type: string
  name: string
  enabled: boolean
  config: Record<string, unknown>
}

export type NotificationRule = {
  id: string
  name: string
  event: string
  channels: string[]
  cooldown_sec: number
  enabled: boolean
}

export type AutomationRule = {
  id: string
  project: string | null
  name: string
  priority: number
  enabled: boolean
  match: Record<string, unknown>
  action: Record<string, unknown>
}

export type AgentRelease = {
  id: string
  version: string
  changelog: string
  checksum_sha256: string
  download_url: string
  is_active: boolean
  created_at: string
}

export function listPlugins(token: string) {
  return apiRequest<{ plugin_api_version: string; results: PluginInfo[] }>(
    '/plugins/',
    { token },
  )
}

export function installPlugin(
  token: string,
  body: { plugin_id: string; config?: Record<string, unknown>; enabled?: boolean },
) {
  return apiRequest('/plugins/install/', { method: 'POST', token, body })
}

export function updatePlugin(
  token: string,
  pluginId: string,
  body: Partial<{ enabled: boolean; config: Record<string, unknown> }>,
) {
  return apiRequest(`/plugins/${pluginId}/`, { method: 'PATCH', token, body })
}

export function listNotificationChannels(token: string) {
  return apiRequest<{ results: NotificationChannel[] }>('/notifications/channels/', {
    token,
  })
}

export function createNotificationChannel(
  token: string,
  body: {
    channel_type: string
    name?: string
    enabled?: boolean
    config?: Record<string, unknown>
  },
) {
  return apiRequest<NotificationChannel>('/notifications/channels/', {
    method: 'POST',
    token,
    body,
  })
}

export function listNotificationRules(token: string) {
  return apiRequest<{ results: NotificationRule[] }>('/notifications/rules/', { token })
}

export function createNotificationRule(
  token: string,
  body: {
    name: string
    event: string
    channels: string[]
    cooldown_sec?: number
  },
) {
  return apiRequest<NotificationRule>('/notifications/rules/', {
    method: 'POST',
    token,
    body,
  })
}

export function listAutomations(token: string) {
  return apiRequest<{ results: AutomationRule[] }>('/automations/', { token })
}

export function createAutomation(
  token: string,
  body: {
    name: string
    priority?: number
    match: Record<string, unknown>
    action: Record<string, unknown>
    project?: string | null
  },
) {
  return apiRequest<AutomationRule>('/automations/', { method: 'POST', token, body })
}

export function deleteAutomation(token: string, id: string) {
  return apiRequest<void>(`/automations/${id}/`, { method: 'DELETE', token })
}

export function listAgentReleases(token: string) {
  return apiRequest<{ results: AgentRelease[] }>('/agent/releases/', { token })
}

export function createAgentRelease(
  token: string,
  body: { version: string; download_url?: string; changelog?: string },
) {
  return apiRequest<AgentRelease>('/agent/releases/', { method: 'POST', token, body })
}

export function pushOta(token: string, deviceId: string, releaseId?: string) {
  return apiRequest(`/devices/${deviceId}/ota/`, {
    method: 'POST',
    token,
    body: releaseId ? { release_id: releaseId } : {},
  })
}
