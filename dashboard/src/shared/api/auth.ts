import { apiRequest } from './client'
import type { AuthResponse, User, Tenant } from '../lib/types'

export type RegisterPayload = {
  email: string
  password: string
  name?: string
  tenant_name: string
  tenant_slug?: string
  locale?: 'en' | 'fa'
}

export type LoginPayload = {
  email: string
  password: string
  tenant_slug?: string
}

export function register(payload: RegisterPayload) {
  return apiRequest<AuthResponse>('/auth/register/', {
    method: 'POST',
    body: payload,
  })
}

export function login(payload: LoginPayload) {
  return apiRequest<AuthResponse>('/auth/login/', {
    method: 'POST',
    body: payload,
  })
}

export function fetchMe(token: string) {
  return apiRequest<{ user: User; memberships: Array<{ role: string; tenant: Tenant }> }>(
    '/auth/me/',
    { token },
  )
}

export function fetchTenantMe(token: string) {
  return apiRequest<{
    tenant: Tenant
    role: string
    permissions: string[]
  }>('/tenants/me/', { token })
}
