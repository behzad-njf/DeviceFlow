import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { listAuditLogs, type AuditEntry } from '../../shared/api/enterprise'
import { useAuthStore } from '../../features/auth/authStore'

export function AuditPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [items, setItems] = useState<AuditEntry[]>([])
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!token) return
    const res = await listAuditLogs(token)
    setItems(res.results)
  }, [token])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refresh, t])

  return (
    <div>
      <header className="page-header">
        <h1>{t('audit.title')}</h1>
        <p>{t('audit.subtitle')}</p>
      </header>
      {error ? <div className="auth-error">{error}</div> : null}
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('audit.time')}</th>
              <th>{t('audit.actor')}</th>
              <th>{t('audit.action')}</th>
              <th>{t('audit.object')}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id}>
                <td>{new Date(row.created_at).toLocaleString()}</td>
                <td>{row.actor_email || row.actor_label || row.actor_type}</td>
                <td>
                  <code>{row.action}</code>
                </td>
                <td>
                  {row.object_type}
                  {row.object_id ? `:${row.object_id.slice(0, 8)}` : ''}
                </td>
              </tr>
            ))}
            {!items.length ? (
              <tr>
                <td colSpan={4}>{t('audit.empty')}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
