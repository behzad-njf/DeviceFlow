import { apiRequest } from '../api/client'

export type SimSlot = {
  id: string
  slot_index: number
  operator: string
  phone_number: string
  is_active: boolean
}

export type Device = {
  id: string
  name: string
  status: string
  agent_version: string
  last_seen_at: string | null
  health: Record<string, unknown>
  health_score: number
  capabilities: string[]
  meta?: Record<string, unknown>
  is_paired: boolean
  sims: SimSlot[]
  created_at: string
}

export type PairingCodeResponse = {
  device_id: string
  name: string
  code: string
  expires_at: string
}

export function listDevices(token: string) {
  return apiRequest<{ results: Device[] }>('/devices/', { token })
}

export function createPairingCode(token: string, name?: string) {
  return apiRequest<PairingCodeResponse>('/devices/pairing-code/', {
    method: 'POST',
    token,
    body: { name: name || '' },
  })
}

export function getDeviceQueue(token: string, deviceId: string) {
  return apiRequest<{
    pending: number
    sending: number
    failed: number
    dead_letter: number
  }>(`/devices/${deviceId}/queue/`, { token })
}
