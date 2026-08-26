import { apiRequest } from '../api/client'

export type ProjectDevice = {
  device_id: string
  name: string
  status: string
  agent_version: string
  health_score: number
  last_seen_at: string | null
  priority: number
  exclusive: boolean
  preferred_sim_slot: number | null
  sim_fallback_enabled: boolean
}

export type ProjectDeviceSettings = {
  preferred_sim_slot?: number | null
  sim_fallback_enabled?: boolean
  priority?: number
}

export type Project = {
  id: string
  name: string
  slug: string
  mode_default: string
  is_active: boolean
  device_count?: number
  devices?: ProjectDevice[]
  created_at?: string
  updated_at?: string
}

export function listProjects(token: string) {
  return apiRequest<{ results: Project[] }>('/projects/', { token })
}

export function createProject(
  token: string,
  payload: { name: string; slug: string; mode_default?: string },
) {
  return apiRequest<Project>('/projects/', {
    method: 'POST',
    token,
    body: payload,
  })
}

export function getProjectDevices(token: string, projectId: string) {
  return apiRequest<{ results: ProjectDevice[] }>(`/projects/${projectId}/devices/`, {
    token,
  })
}

export function setProjectDevices(
  token: string,
  projectId: string,
  deviceIds: string[],
  deviceSettings?: Record<string, ProjectDeviceSettings>,
) {
  return apiRequest<{ results: ProjectDevice[] }>(`/projects/${projectId}/devices/`, {
    method: 'PUT',
    token,
    body: {
      device_ids: deviceIds,
      device_settings: deviceSettings,
    },
  })
}
