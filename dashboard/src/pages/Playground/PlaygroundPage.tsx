import { useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../../features/auth/authStore'
import { Button, Field, TextInput } from '../../shared/ui/Form'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') || '/api/v1'

export function PlaygroundPage() {
  const { t } = useTranslation()
  const jwt = useAuthStore((s) => s.accessToken)
  const [method, setMethod] = useState('POST')
  const [path, setPath] = useState('/messages/send/')
  const [authMode, setAuthMode] = useState<'jwt' | 'apikey'>('jwt')
  const [apiKey, setApiKey] = useState('')
  const [idempotencyKey, setIdempotencyKey] = useState('')
  const [body, setBody] = useState(
    JSON.stringify(
      { to: '+989121234567', text: 'Hello from playground', project: 'api' },
      null,
      2,
    ),
  )
  const [status, setStatus] = useState<number | null>(null)
  const [response, setResponse] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function onSend(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setResponse('')
    setStatus(null)
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    }
    if (authMode === 'jwt' && jwt) {
      headers.Authorization = `Bearer ${jwt}`
    } else if (authMode === 'apikey' && apiKey) {
      headers.Authorization = `ApiKey ${apiKey}`
    }
    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey
    }
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: ['GET', 'HEAD'].includes(method) ? undefined : body,
      })
      setStatus(res.status)
      const text = await res.text()
      try {
        setResponse(JSON.stringify(JSON.parse(text), null, 2))
      } catch {
        setResponse(text)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('common.error'))
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('playground.title')}</h1>
        <p>{t('playground.subtitle')}</p>
      </header>

      <section className="panel" style={{ marginBottom: 24 }}>
        <form className="auth-form" onSubmit={(e) => void onSend(e)}>
          <div className="toolbar">
            <Field label={t('playground.method')} htmlFor="pg-method">
              <select
                id="pg-method"
                className="df-input"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
              >
                {['GET', 'POST', 'PATCH', 'PUT', 'DELETE'].map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t('playground.path')} htmlFor="pg-path">
              <TextInput
                id="pg-path"
                value={path}
                onChange={(e) => setPath(e.target.value)}
              />
            </Field>
            <Field label={t('playground.auth')} htmlFor="pg-auth">
              <select
                id="pg-auth"
                className="df-input"
                value={authMode}
                onChange={(e) => setAuthMode(e.target.value as 'jwt' | 'apikey')}
              >
                <option value="jwt">JWT</option>
                <option value="apikey">API Key</option>
              </select>
            </Field>
          </div>
          {authMode === 'apikey' ? (
            <Field label={t('playground.apiKey')} htmlFor="pg-key">
              <TextInput
                id="pg-key"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="df_live_…"
              />
            </Field>
          ) : null}
          <Field label={t('playground.idempotency')} htmlFor="pg-idem">
            <TextInput
              id="pg-idem"
              value={idempotencyKey}
              onChange={(e) => setIdempotencyKey(e.target.value)}
              placeholder="optional"
            />
          </Field>
          <Field label={t('playground.body')} htmlFor="pg-body">
            <textarea
              id="pg-body"
              className="df-input"
              rows={10}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              style={{ fontFamily: 'ui-monospace, monospace', fontSize: 13 }}
            />
          </Field>
          <Button type="submit">{t('playground.send')}</Button>
        </form>
      </section>

      {error ? <div className="auth-error">{error}</div> : null}
      {status !== null ? (
        <section className="panel">
          <h2 style={{ fontSize: 16, marginBottom: 8 }}>
            {t('playground.response')} · HTTP {status}
          </h2>
          <pre
            style={{
              margin: 0,
              overflow: 'auto',
              fontSize: 12,
              maxHeight: 420,
            }}
          >
            {response}
          </pre>
        </section>
      ) : null}

      <p style={{ marginTop: 16, color: 'var(--text-muted)', fontSize: 13 }}>
        {t('playground.docsHint')}{' '}
        <a href="/api/v1/docs/" target="_blank" rel="noreferrer">
          /api/v1/docs/
        </a>
      </p>
    </div>
  )
}
