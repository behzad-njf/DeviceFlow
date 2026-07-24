import { apiRequest } from '../api/client'

export type Message = {
  id: string
  to_number: string
  body: string
  status: string
  mode: string
  device: string | null
  device_name: string | null
  project: string | null
  project_name: string | null
  sim_slot_index: number | null
  retry_count: number
  latency_ms: number | null
  error_message: string
  created_at: string
  sent_at: string | null
}

export type InboundMessage = {
  id: string
  from_number: string
  body: string
  device_name: string
  received_at: string
}

export function listMessages(token: string) {
  return apiRequest<{ results: Message[] }>('/messages/', { token })
}

export function sendMessage(
  token: string,
  payload: {
    to: string
    text: string
    project?: string
    device?: string
    sim_slot?: number
  },
) {
  return apiRequest<Message>('/messages/send/', {
    method: 'POST',
    token,
    body: payload,
  })
}

export function retryMessage(token: string, id: string) {
  return apiRequest<Message>(`/messages/${id}/retry/`, { method: 'POST', token })
}

export function cancelMessage(token: string, id: string) {
  return apiRequest<Message>(`/messages/${id}/cancel/`, { method: 'POST', token })
}

export function listInbound(token: string) {
  return apiRequest<{ results: InboundMessage[] }>('/inbound/', { token })
}
