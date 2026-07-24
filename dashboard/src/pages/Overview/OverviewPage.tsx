import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchAnalyticsOverview, type AnalyticsOverview } from '../../shared/api/ops'
import { scanAnomalies, type AnomalyFinding } from '../../shared/api/ai'
import { Button } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'

export function OverviewPage() {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const tenant = useAuthStore((s) => s.tenant)
  const role = useAuthStore((s) => s.role)
  const token = useAuthStore((s) => s.accessToken)
  const [stats, setStats] = useState<AnalyticsOverview | null>(null)
  const [findings, setFindings] = useState<AnomalyFinding[]>([])

  const refresh = useCallback(async () => {
    if (!token) return
    setStats(await fetchAnalyticsOverview(token))
  }, [token])

  useEffect(() => {
    void refresh().catch(() => undefined)
  }, [refresh])

  async function onScan() {
    if (!token) return
    const res = await scanAnomalies(token, true)
    setFindings(res.results)
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('overview.title')}</h1>
        <p>{t('overview.subtitle')}</p>
      </header>

      <div className="meta-row">
        <span>{t('overview.welcome', { name: user?.name || user?.email })}</span>
        <span>
          {t('overview.tenant')}: <strong>{tenant?.name}</strong>
        </span>
        <span>
          {t('overview.role')}: <strong>{role}</strong>
        </span>
      </div>

      <div className="stat-row">
        <div className="stat-tile">
          <div className="label">{t('overview.statsOnline')}</div>
          <div className="value">{stats?.devices.online ?? t('overview.placeholder')}</div>
        </div>
        <div className="stat-tile">
          <div className="label">{t('overview.statsSent')}</div>
          <div className="value">
            {stats?.messages.sent_today ?? t('overview.placeholder')}
          </div>
        </div>
        <div className="stat-tile">
          <div className="label">{t('overview.statsQueue')}</div>
          <div className="value">
            {stats?.messages.queue_depth ?? t('overview.placeholder')}
          </div>
        </div>
      </div>

      <section className="panel" style={{ marginBottom: 16 }}>
        <div className="toolbar">
          <Button type="button" variant="secondary" onClick={() => void onScan()}>
            {t('overview.aiScan')}
          </Button>
        </div>
        {findings.length ? (
          <ul style={{ marginTop: 12 }}>
            {findings.map((f, i) => (
              <li key={`${f.type}-${i}`}>{f.explanation}</li>
            ))}
          </ul>
        ) : (
          <p className="muted-text" style={{ marginTop: 8 }}>
            {t('overview.aiScanHint')}
          </p>
        )}
      </section>

      <section className="panel">
        <p>{t('overview.phaseNote')}</p>
        {stats?.series_7d?.length ? (
          <div className="series-list">
            {stats.series_7d.map((row) => (
              <div key={String(row.day)} className="series-item">
                <span>{row.day}</span>
                <strong>{row.sent}</strong>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  )
}
