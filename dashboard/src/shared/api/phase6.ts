import { apiRequest } from './client'

export type Contact = {
  id: string
  phone_number: string
  name: string
  tags: string[]
  is_blacklisted: boolean
  is_whitelisted: boolean
  notes: string
  source_device?: string | null
  source_device_name?: string | null
  meta?: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export type ContactImportRow = {
  name?: string
  phone?: string
  phone_number?: string
  number?: string
}

export type ContactImportPreviewRow = {
  name: string
  phone: string
  phone_raw?: string
  exists?: boolean
  existing_id?: string | null
  existing_name?: string
  reason?: string
  normalized?: string
}

export type ContactImportPreview = {
  valid: ContactImportPreviewRow[]
  invalid: ContactImportPreviewRow[]
  summary: {
    total: number
    valid: number
    invalid: number
    already_exist: number
  }
}

export type ContactImportResult = {
  created: number
  updated: number
  skipped: number
  rejected: number
  invalid: ContactImportPreviewRow[]
  imported: Array<{ id: string; phone: string; name: string; action: string }>
  summary: Record<string, number>
}

export type Conversation = {
  id: string
  phone_number: string
  contact_name: string
  last_preview: string
  last_message_at: string | null
  unread_count: number
}

export type BulkCampaign = {
  id: string
  name: string
  status: string
  total: number
  sent: number
  failed: number
  created_at: string
}

export type ExportJob = {
  id: string
  export_type: string
  format: string
  status: string
  row_count: number
  error: string
  created_at: string
}

export function listContacts(
  token: string,
  opts: { q?: string; device?: string; blacklisted?: boolean } = {},
) {
  const qs = new URLSearchParams()
  if (opts.q) qs.set('q', opts.q)
  if (opts.device) qs.set('device', opts.device)
  if (opts.blacklisted) qs.set('blacklisted', '1')
  const suffix = qs.toString() ? `?${qs}` : ''
  return apiRequest<{ results: Contact[] }>(`/contacts/${suffix}`, { token })
}

export function createContact(
  token: string,
  body: Partial<Contact> & { phone_number: string },
) {
  return apiRequest<Contact>('/contacts/', { method: 'POST', token, body })
}

export function updateContact(token: string, id: string, body: Partial<Contact>) {
  return apiRequest<Contact>(`/contacts/${id}/`, { method: 'PATCH', token, body })
}

export function previewContactImport(
  token: string,
  body: { device_id?: string; contacts: ContactImportRow[] },
) {
  return apiRequest<ContactImportPreview>('/contacts/import/preview/', {
    method: 'POST',
    token,
    body,
  })
}

export function confirmContactImport(
  token: string,
  body: {
    device_id?: string
    contacts: ContactImportRow[]
    update_existing?: boolean
  },
) {
  return apiRequest<ContactImportResult>('/contacts/import/', {
    method: 'POST',
    token,
    body,
  })
}

export function listConversations(token: string) {
  return apiRequest<{ results: Conversation[] }>('/conversations/', { token })
}

export function getConversation(token: string, id: string) {
  return apiRequest<{
    conversation: Conversation
    messages: Array<{ direction: string; at: string; message: Record<string, unknown> }>
  }>(`/conversations/${id}/`, { token })
}

export function sendBulk(
  token: string,
  body: {
    project?: string
    name?: string
    messages: Array<{ to: string; text: string }>
  },
) {
  return apiRequest<BulkCampaign>('/messages/send-bulk/', {
    method: 'POST',
    token,
    body,
  })
}

export function listBulkCampaigns(token: string) {
  return apiRequest<{ results: BulkCampaign[] }>('/bulk-campaigns/', { token })
}

export function createExport(
  token: string,
  body: { type?: string; format?: string; filters?: Record<string, string> },
) {
  return apiRequest<ExportJob>('/exports/', { method: 'POST', token, body })
}

export function getExport(token: string, id: string) {
  return apiRequest<ExportJob>(`/exports/${id}/`, { token })
}
