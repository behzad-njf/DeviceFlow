import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { listProjects, type Project } from '../../shared/api/projects'
import {
  createWebhook,
  listWebhookDeliveries,
  listWebhooks,
  redeliverWebhook,
  type WebhookDelivery,
  type WebhookEndpoint,
} from '../../shared/api/developer'
import { apiRequest } from '../../shared/api/client'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'

const EVENT_OPTIONS = [
  'message.queued',
  'message.assigned',
  'message.sent',
  'message.delivered',
  'message.failed',
  'message.dead_letter',
  'inbound.received',
  'device.offline',
  'device.online',
  'automation.triggered',
]

export function WebhooksPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState('')
  const [hooks, setHooks] = useState<WebhookEndpoint[]>([])
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([])
  const [url, setUrl] = useState('https://example.com/hooks/deviceflow')
  const [events, setEvents] = useState<string[]>(['inbound.received', 'message.failed'])
  const [description, setDescription] = useState('')
  const [secretOnce, setSecretOnce] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!token) return
    const p = await listProjects(token)
    setProjects(p.results)
    const pid = projectId || p.results[0]?.id || ''
    if (!projectId && pid) setProjectId(pid)
    if (!pid) return
    const [h, d] = await Promise.all([
      listWebhooks(token, pid),
      listWebhookDeliveries(token, pid),
    ])
    setHooks(h.results)
    setDeliveries(d.results)
  }, [token, projectId])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refresh, t])

  function toggleEvent(ev: string) {
    setEvents((prev) =>
      prev.includes(ev) ? prev.filter((x) => x !== ev) : [...prev, ev],
    )
  }

  async function onCreate(event: FormEvent) {
    event.preventDefault()
    if (!token || !projectId) return
    try {
      const created = await createWebhook(token, projectId, {
        url,
        events: events.length ? events : ['*'],
        description,
      })
      setSecretOnce(created.secret || null)
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function onDelete(hook: WebhookEndpoint) {
    if (!token || !projectId) return
    try {
      await apiRequest(`/projects/${projectId}/webhooks/${hook.id}/`, {
        method: 'DELETE',
        token,
      })
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function onToggle(hook: WebhookEndpoint) {
    if (!token || !projectId) return
    try {
      await apiRequest(`/projects/${projectId}/webhooks/${hook.id}/`, {
        method: 'PATCH',
        token,
        body: { is_active: !hook.is_active },
      })
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('webhooks.title')}</h1>
        <p>{t('webhooks.subtitle')}</p>
      </header>

      <section className="panel" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>{t('webhooks.builder')}</h2>
        <form className="auth-form" onSubmit={(e) => void onCreate(e)}>
          <div className="toolbar">
            <Field label={t('webhooks.project')} htmlFor="wh-project">
              <select
                id="wh-project"
                className="df-input"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t('webhooks.url')} htmlFor="wh-url">
              <TextInput id="wh-url" value={url} onChange={(e) => setUrl(e.target.value)} required />
            </Field>
            <Field label={t('webhooks.description')} htmlFor="wh-desc">
              <TextInput
                id="wh-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </Field>
            <Button type="submit">{t('webhooks.create')}</Button>
          </div>
          <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {EVENT_OPTIONS.map((ev) => (
              <label key={ev} className="checkbox-row" style={{ margin: 0 }}>
                <input
                  type="checkbox"
                  checked={events.includes(ev)}
                  onChange={() => toggleEvent(ev)}
                />
                {ev}
              </label>
            ))}
          </div>
        </form>
        {secretOnce ? (
          <div className="auth-error" style={{ marginTop: 12 }}>
            {t('webhooks.secretOnce')}: <code>{secretOnce}</code>
          </div>
        ) : null}
      </section>

      {error ? <div className="auth-error">{error}</div> : null}

      <div className="table-wrap" style={{ marginBottom: 24 }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('webhooks.url')}</th>
              <th>{t('webhooks.events')}</th>
              <th>{t('webhooks.failures')}</th>
              <th>{t('webhooks.active')}</th>
              <th>{t('webhooks.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {hooks.map((h) => (
              <tr key={h.id}>
                <td>{h.url}</td>
                <td>{(h.events || []).join(', ') || '—'}</td>
                <td>{h.failure_count}</td>
                <td>{h.is_active ? 'yes' : 'no'}</td>
                <td>
                  <button
                    type="button"
                    className="df-btn df-btn-ghost"
                    onClick={() => void onToggle(h)}
                  >
                    {h.is_active ? t('webhooks.disable') : t('webhooks.enable')}
                  </button>
                  <button
                    type="button"
                    className="df-btn df-btn-ghost"
                    onClick={() => void onDelete(h)}
                  >
                    {t('webhooks.delete')}
                  </button>
                </td>
              </tr>
            ))}
            {!hooks.length ? (
              <tr>
                <td colSpan={5}>{t('webhooks.empty')}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('webhooks.event')}</th>
              <th>{t('webhooks.status')}</th>
              <th>{t('webhooks.attempts')}</th>
              <th>{t('webhooks.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {deliveries.map((d) => (
              <tr key={d.id}>
                <td>{d.event_type}</td>
                <td>{d.status}</td>
                <td>{d.attempts}</td>
                <td>
                  <button
                    type="button"
                    className="df-btn df-btn-ghost"
                    onClick={() =>
                      token && void redeliverWebhook(token, d.id).then(() => refresh())
                    }
                  >
                    {t('webhooks.redeliver')}
                  </button>
                </td>
              </tr>
            ))}
            {!deliveries.length ? (
              <tr>
                <td colSpan={4}>{t('webhooks.emptyDeliveries')}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
