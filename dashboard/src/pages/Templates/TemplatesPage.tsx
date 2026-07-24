import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import {
  createTemplate,
  deleteTemplate,
  listTemplates,
  renderTemplate,
  type MessageTemplate,
} from '../../shared/api/developer'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'

export function TemplatesPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [items, setItems] = useState<MessageTemplate[]>([])
  const [name, setName] = useState('')
  const [body, setBody] = useState('Hello {{name}}, code {{code}}')
  const [preview, setPreview] = useState('')
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!token) return
    const res = await listTemplates(token)
    setItems(res.results)
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
      await createTemplate(token, { name, body })
      setName('')
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function onPreview(tpl: MessageTemplate) {
    if (!token) return
    try {
      const vars: Record<string, string> = {}
      for (const v of tpl.variables) vars[v] = v === 'code' ? '123456' : 'Demo'
      const res = await renderTemplate(token, tpl.id, vars)
      setPreview(res.text)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('templates.title')}</h1>
        <p>{t('templates.subtitle')}</p>
      </header>

      <section className="panel" style={{ marginBottom: 24 }}>
        <form className="auth-form" onSubmit={(e) => void onCreate(e)}>
          <Field label={t('templates.name')} htmlFor="tpl-name">
            <TextInput id="tpl-name" value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label={t('templates.body')} htmlFor="tpl-body">
            <textarea
              id="tpl-body"
              className="df-input"
              rows={3}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
            />
          </Field>
          <Button type="submit">{t('templates.create')}</Button>
        </form>
        {preview ? (
          <p style={{ marginTop: 12 }}>
            {t('templates.preview')}: <strong>{preview}</strong>
          </p>
        ) : null}
      </section>

      {error ? <div className="auth-error">{error}</div> : null}

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('templates.name')}</th>
              <th>{t('templates.body')}</th>
              <th>{t('templates.vars')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((tpl) => (
              <tr key={tpl.id}>
                <td>{tpl.name}</td>
                <td>
                  <code style={{ fontSize: 12 }}>{tpl.body}</code>
                </td>
                <td>{tpl.variables.join(', ')}</td>
                <td>
                  <button
                    type="button"
                    className="df-btn df-btn-ghost"
                    onClick={() => void onPreview(tpl)}
                  >
                    {t('templates.preview')}
                  </button>
                  <button
                    type="button"
                    className="df-btn df-btn-ghost"
                    onClick={() =>
                      void deleteTemplate(token!, tpl.id).then(() => refresh())
                    }
                  >
                    {t('templates.delete')}
                  </button>
                </td>
              </tr>
            ))}
            {!items.length ? (
              <tr>
                <td colSpan={4}>{t('templates.empty')}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
