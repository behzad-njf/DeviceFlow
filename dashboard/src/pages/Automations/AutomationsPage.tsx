import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import {
  createAutomation,
  deleteAutomation,
  listAutomations,
  type AutomationRule,
} from '../../shared/api/extensibility'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'

export function AutomationsPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [rules, setRules] = useState<AutomationRule[]>([])
  const [name, setName] = useState('Inbound STOP → webhook')
  const [contains, setContains] = useState('STOP')
  const [webhookUrl, setWebhookUrl] = useState('https://example.com/hooks/stop')
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!token) return
    setRules((await listAutomations(token)).results)
  }, [token])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refresh, t])

  async function onCreate(event: FormEvent) {
    event.preventDefault()
    if (!token) return
    try {
      await createAutomation(token, {
        name,
        priority: 100,
        match: { event: 'inbound.received', body_contains: contains },
        action: { type: 'webhook', url: webhookUrl, stop: true },
      })
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function onDelete(id: string) {
    if (!token) return
    try {
      await deleteAutomation(token, id)
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('automations.title')}</h1>
        <p>{t('automations.subtitle')}</p>
      </header>
      {error ? <div className="auth-error">{error}</div> : null}

      <section className="panel" style={{ marginBottom: 24 }}>
        <form className="auth-form" onSubmit={(e) => void onCreate(e)}>
          <div className="toolbar">
            <Field label={t('automations.name')} htmlFor="aname">
              <TextInput id="aname" value={name} onChange={(e) => setName(e.target.value)} required />
            </Field>
            <Field label={t('automations.contains')} htmlFor="acontains">
              <TextInput
                id="acontains"
                value={contains}
                onChange={(e) => setContains(e.target.value)}
                required
              />
            </Field>
            <Field label={t('automations.webhook')} htmlFor="aurl">
              <TextInput
                id="aurl"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                required
              />
            </Field>
            <Button type="submit">{t('automations.create')}</Button>
          </div>
        </form>
      </section>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('automations.name')}</th>
              <th>{t('automations.match')}</th>
              <th>{t('automations.action')}</th>
              <th>{t('automations.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>
                  <code style={{ fontSize: 12 }}>{JSON.stringify(r.match)}</code>
                </td>
                <td>
                  <code style={{ fontSize: 12 }}>{JSON.stringify(r.action)}</code>
                </td>
                <td>
                  <button
                    type="button"
                    className="df-btn df-btn-ghost"
                    onClick={() => void onDelete(r.id)}
                  >
                    {t('automations.delete')}
                  </button>
                </td>
              </tr>
            ))}
            {!rules.length ? (
              <tr>
                <td colSpan={4}>{t('automations.empty')}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
