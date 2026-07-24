import { apiRequest } from './client'

export type Membership = {
  id: string
  email: string
  name: string
  role: string
  is_active: boolean
}

export type Invite = {
  id: string
  email: string
  role: string
  expires_at: string
  token?: string
  accept_hint?: string
}

export type AuditEntry = {
  id: string
  action: string
  object_type: string
  object_id: string
  actor_type: string
  actor_label: string
  actor_email: string | null
  created_at: string
  after: Record<string, unknown>
}

export function listUsers(token: string) {
  return apiRequest<{ results: Membership[] }>('/users/', { token })
}

export function inviteUser(
  token: string,
  body: { email: string; role: string },
) {
  return apiRequest<Invite>('/users/invite/', { method: 'POST', token, body })
}

export function updateMembership(
  token: string,
  id: string,
  body: { role?: string; is_active?: boolean },
) {
  return apiRequest<Membership>(`/users/${id}/`, { method: 'PATCH', token, body })
}

export function listAuditLogs(token: string) {
  return apiRequest<{ results: AuditEntry[] }>('/audit-logs/', { token })
}
