import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { fetchQueuesSummary, type QueueSummary } from '../../shared/api/ops'
import { useAuthStore } from '../../features/auth/authStore'
import { dashboardSocket } from '../../shared/ws/client'

export function QueuesPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [data, setData] = useState<QueueSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!token) return
    setData(await fetchQueuesSummary(token))
  }, [token])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
    const id = window.setInterval(() => {
      void refresh().catch(() => undefined)
    }, 5000)
    return () => window.clearInterval(id)
  }, [refresh, t])

  useEffect(() => {
    return dashboardSocket.onEvent((event) => {
      if (event.type === 'queue.updated' || event.type === 'message.updated') {
        void refresh().catch(() => undefined)
      }
    })
  }, [refresh])

  return (
    <div>
      <header className="page-header">
        <h1>{t('queues.title')}</h1>
        <p>{t('queues.subtitle')}</p>
      </header>

      {error ? <div className="auth-error">{error}</div> : null}

      <div className="stat-row">
        <div className="stat-tile">
          <div className="label">{t('queues.pending')}</div>
          <div className="value">{data?.totals.pending ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">{t('queues.sending')}</div>
          <div className="value">{data?.totals.sending ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">{t('queues.failed')}</div>
          <div className="value">{data?.totals.failed ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">{t('queues.dead')}</div>
          <div className="value">{data?.totals.dead_letter ?? '—'}</div>
        </div>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('devices.colName')}</th>
              <th>{t('devices.colStatus')}</th>
              <th>{t('queues.pending')}</th>
              <th>{t('queues.sending')}</th>
              <th>{t('queues.failed')}</th>
              <th>{t('queues.dead')}</th>
            </tr>
          </thead>
          <tbody>
            {(data?.results || []).map((row) => (
              <tr key={row.device_id}>
                <td>
                  <Link to={`/devices/${row.device_id}`}>{row.name}</Link>
                </td>
                <td>
                  <span className={`status-chip status-${row.status}`}>{row.status}</span>
                </td>
                <td>{row.pending}</td>
                <td>{row.sending}</td>
                <td>{row.failed}</td>
                <td>{row.dead_letter}</td>
              </tr>
            ))}
            {!data?.results.length ? (
              <tr>
                <td colSpan={6}>{t('queues.empty')}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
