import type { Device } from '../api/devices'

/** Matches backend DEVICE_OFFLINE_AFTER_SECONDS default (45). */
export const DEVICE_STALE_AFTER_MS = 45_000

/**
 * Derive display status. If Celery beat is not running, the API may keep
 * status=online forever; treat missed heartbeats as offline in the UI.
 */
export function displayDeviceStatus(
  device: Pick<Device, 'status' | 'last_seen_at'>,
  nowMs: number = Date.now(),
): string {
  if (device.status === 'disabled' || device.status === 'pending') {
    return device.status
  }
  if (device.status === 'online' || device.status === 'busy') {
    if (!device.last_seen_at) return 'offline'
    const age = nowMs - new Date(device.last_seen_at).getTime()
    if (Number.isFinite(age) && age > DEVICE_STALE_AFTER_MS) {
      return 'offline'
    }
  }
  return device.status
}

export function applyDeviceUpdate(
  prev: Device,
  payload: Record<string, unknown>,
): Device {
  return {
    ...prev,
    name: typeof payload.name === 'string' ? payload.name : prev.name,
    status: typeof payload.status === 'string' ? payload.status : prev.status,
    agent_version:
      typeof payload.agent_version === 'string'
        ? payload.agent_version
        : prev.agent_version,
    last_seen_at:
      typeof payload.last_seen_at === 'string' || payload.last_seen_at === null
        ? (payload.last_seen_at as string | null)
        : prev.last_seen_at,
    health:
      payload.health && typeof payload.health === 'object'
        ? (payload.health as Record<string, unknown>)
        : prev.health,
    health_score:
      typeof payload.health_score === 'number'
        ? payload.health_score
        : prev.health_score,
    is_paired:
      typeof payload.is_paired === 'boolean' ? payload.is_paired : prev.is_paired,
    meta:
      payload.meta && typeof payload.meta === 'object'
        ? (payload.meta as Record<string, unknown>)
        : prev.meta,
  }
}
