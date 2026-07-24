import { apiRequest } from './client'

export type ApiKey = {
  id: string
  project_id: string
  project_slug: string
  name: string
  key_prefix: string
  scopes: string[]
  ip_whitelist: string[]
  last_used_at: string | null
  usage_count?: number
  messages_sent?: number
  revoked_at: string | null
  is_active: boolean
  created_at: string
  key?: string
}

export type WebhookEndpoint = {
  id: string
  project_id: string
  url: string
  events: string[]
  is_active: boolean
  failure_count: number
  description: string
  secret?: string
}

export type WebhookDelivery = {
  id: string
  endpoint: string
  endpoint_url: string
  event_type: string
  status: string
  attempts: number
  response_code: number | null
  created_at: string
}

export type MessageTemplate = {
  id: string
  project: string | null
  name: string
  body: string
  channel: string
  is_active: boolean
  variables: string[]
}

export function listApiKeys(token: string, projectId: string) {
  return apiRequest<{ results: ApiKey[] }>(`/projects/${projectId}/api-keys/`, { token })
}

export function createApiKey(
  token: string,
  projectId: string,
  body: { name: string; scopes?: string[]; ip_whitelist?: string[] },
) {
  return apiRequest<ApiKey>(`/projects/${projectId}/api-keys/`, {
    method: 'POST',
    token,
    body,
  })
}

export function revokeApiKey(token: string, projectId: string, keyId: string) {
  return apiRequest<ApiKey>(`/projects/${projectId}/api-keys/${keyId}/revoke/`, {
    method: 'POST',
    token,
  })
}

export function deleteApiKey(token: string, projectId: string, keyId: string) {
  return apiRequest<void>(`/projects/${projectId}/api-keys/${keyId}/`, {
    method: 'DELETE',
    token,
  })
}

export function listWebhooks(token: string, projectId: string) {
  return apiRequest<{ results: WebhookEndpoint[] }>(
    `/projects/${projectId}/webhooks/`,
    { token },
  )
}

export function createWebhook(
  token: string,
  projectId: string,
  body: { url: string; events?: string[]; description?: string },
) {
  return apiRequest<WebhookEndpoint>(`/projects/${projectId}/webhooks/`, {
    method: 'POST',
    token,
    body,
  })
}

export function listWebhookDeliveries(token: string, projectId?: string) {
  const q = projectId ? `?project=${projectId}` : ''
  return apiRequest<{ results: WebhookDelivery[] }>(`/webhooks/deliveries/${q}`, {
    token,
  })
}

export function redeliverWebhook(token: string, deliveryId: string) {
  return apiRequest<WebhookDelivery>(`/webhooks/deliveries/${deliveryId}/redeliver/`, {
    method: 'POST',
    token,
  })
}

export function listTemplates(token: string) {
  return apiRequest<{ results: MessageTemplate[] }>('/templates/', { token })
}

export function createTemplate(
  token: string,
  body: { name: string; body: string; project?: string | null },
) {
  return apiRequest<MessageTemplate>('/templates/', {
    method: 'POST',
    token,
    body,
  })
}

export function renderTemplate(
  token: string,
  id: string,
  vars: Record<string, string>,
) {
  return apiRequest<{ text: string }>(`/templates/${id}/render/`, {
    method: 'POST',
    token,
    body: { vars },
  })
}

export function deleteTemplate(token: string, id: string) {
  return apiRequest<void>(`/templates/${id}/`, { method: 'DELETE', token })
}
