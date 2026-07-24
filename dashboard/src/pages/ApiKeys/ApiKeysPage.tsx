import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { listProjects, type Project } from '../../shared/api/projects'
import {
  createApiKey,
  deleteApiKey,
  listApiKeys,
  revokeApiKey,
  type ApiKey,
} from '../../shared/api/developer'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { Modal } from '../../shared/ui/Modal'
import { useAuthStore } from '../../features/auth/authStore'

function formatWhen(value: string | null | undefined, neverLabel: string) {
  if (!value) return neverLabel
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

export function ApiKeysPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState('')
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [name, setName] = useState('default')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createdKey, setCreatedKey] = useState<ApiKey | null>(null)
  const [copied, setCopied] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<ApiKey | null>(null)
  const [deleting, setDeleting] = useState(false)

  const refresh = useCallback(async () => {
    if (!token) return
    const p = await listProjects(token)
    setProjects(p.results)
    const pid = projectId || p.results[0]?.id || ''
    if (!projectId && pid) setProjectId(pid)
    if (!pid) return
    const k = await listApiKeys(token, pid)
    setKeys(k.results)
  }, [token, projectId])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refresh, t])

  async function onCreate(event: FormEvent) {
    event.preventDefault()
    if (!token || !projectId) return
    setBusy(true)
    setError(null)
    setCopied(false)
    try {
      const created = await createApiKey(token, projectId, {
        name: name.trim() || 'default',
        scopes: ['messages.send', 'messages.read', 'inbound.read'],
      })
      setCreatedKey(created)
      setName('default')
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  async function onRevoke(key: ApiKey) {
    if (!token || !projectId) return
    if (!window.confirm(t('apikeys.revokeConfirm', { name: key.name }))) return
    try {
      await revokeApiKey(token, projectId, key.id)
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function confirmDelete() {
    if (!token || !projectId || !deleteTarget) return
    setDeleting(true)
    setError(null)
    try {
      await deleteApiKey(token, projectId, deleteTarget.id)
      setDeleteTarget(null)
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setDeleting(false)
    }
  }

  async function copyKey() {
    const value = createdKey?.key
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('apikeys.title')}</h1>
        <p>{t('apikeys.subtitle')}</p>
      </header>

      {error ? <div className="auth-error">{error}</div> : null}

      <section className="panel apikey-create-panel">
        <h2 className="contacts-section-title">{t('apikeys.create')}</h2>
        <form className="auth-form" onSubmit={(e) => void onCreate(e)}>
          <div className="toolbar">
            <Field label={t('apikeys.project')} htmlFor="apk-project">
              <select
                id="apk-project"
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
            <Field label={t('apikeys.name')} htmlFor="apk-name">
              <TextInput
                id="apk-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="production"
              />
            </Field>
            <Button type="submit" disabled={busy || !projectId}>
              {t('apikeys.create')}
            </Button>
          </div>
        </form>
      </section>

      <div className="apikey-card-list">
        {keys.map((k) => {
          const active = !k.revoked_at
          return (
            <section key={k.id} className={`panel apikey-card ${active ? '' : 'is-revoked'}`}>
              <header className="apikey-card-head">
                <div>
                  <div className="apikey-card-title-row">
                    <h2>{k.name}</h2>
                    <span className={`project-badge ${active ? 'is-on' : 'is-off'}`}>
                      {active ? t('apikeys.active') : t('apikeys.revoked')}
                    </span>
                  </div>
                  <p className="muted-text apikey-prefix">
                    <code>{k.key_prefix}…</code>
                    <span aria-hidden>·</span>
                    {t('apikeys.createdAt')}: {formatWhen(k.created_at, '—')}
                  </p>
                </div>
                <div className="apikey-card-actions">
                  {active ? (
                    <Button type="button" variant="ghost" onClick={() => void onRevoke(k)}>
                      {t('apikeys.revoke')}
                    </Button>
                  ) : null}
                  <Button type="button" variant="ghost" onClick={() => setDeleteTarget(k)}>
                    {t('apikeys.delete')}
                  </Button>
                </div>
              </header>

              <dl className="apikey-stats">
                <div>
                  <dt>{t('apikeys.usageCount')}</dt>
                  <dd>{k.usage_count ?? 0}</dd>
                </div>
                <div>
                  <dt>{t('apikeys.messagesSent')}</dt>
                  <dd>{k.messages_sent ?? 0}</dd>
                </div>
                <div>
                  <dt>{t('apikeys.lastUsed')}</dt>
                  <dd>{formatWhen(k.last_used_at, t('apikeys.neverUsed'))}</dd>
                </div>
              </dl>

              <p className="apikey-scopes muted-text">
                <strong>{t('apikeys.scopes')}:</strong> {(k.scopes || []).join(', ') || '—'}
              </p>
            </section>
          )
        })}
        {!keys.length ? (
          <section className="panel">
            <p>{t('apikeys.empty')}</p>
          </section>
        ) : null}
      </div>

      <Modal
        open={Boolean(createdKey?.key)}
        onClose={() => {
          setCreatedKey(null)
          setCopied(false)
        }}
        title={t('apikeys.createdTitle')}
        footer={
          <div className="toolbar">
            <Button type="button" variant="secondary" onClick={() => void copyKey()}>
              {copied ? t('apikeys.copied') : t('apikeys.copy')}
            </Button>
            <Button
              type="button"
              onClick={() => {
                setCreatedKey(null)
                setCopied(false)
              }}
            >
              {t('apikeys.done')}
            </Button>
          </div>
        }
      >
        <p className="muted-text">{t('apikeys.copyOnce')}</p>
        <div className="apikey-secret-box">
          <code>{createdKey?.key}</code>
        </div>
        <p className="muted-text">{t('apikeys.copyOnceHint')}</p>
      </Modal>

      <Modal
        open={Boolean(deleteTarget)}
        onClose={() => {
          if (!deleting) setDeleteTarget(null)
        }}
        title={t('apikeys.deleteTitle')}
        footer={
          <div className="toolbar">
            <Button
              type="button"
              variant="ghost"
              disabled={deleting}
              onClick={() => setDeleteTarget(null)}
            >
              {t('common.cancel')}
            </Button>
            <Button type="button" disabled={deleting} onClick={() => void confirmDelete()}>
              {deleting ? t('common.loading') : t('apikeys.delete')}
            </Button>
          </div>
        }
      >
        <p>
          {t('apikeys.deleteConfirm', { name: deleteTarget?.name || '' })}
        </p>
        {deleteTarget ? (
          <p className="muted-text">
            <code>{deleteTarget.key_prefix}…</code>
          </p>
        ) : null}
      </Modal>
    </div>
  )
}
