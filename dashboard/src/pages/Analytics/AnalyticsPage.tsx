import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  fetchAnalyticsDevices,
  fetchAnalyticsLatency,
  fetchAnalyticsOperators,
  fetchAnalyticsOverview,
  fetchAnalyticsTimeseries,
  type AnalyticsOverview,
  type DeviceAnalytic,
  type LatencyByMode,
  type OperatorStat,
} from '../../shared/api/analytics'
import { useAuthStore } from '../../features/auth/authStore'

function Bar({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="series-item" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div
        style={{
          height: 8,
          borderRadius: 4,
          background: 'var(--border)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            background: 'var(--accent)',
          }}
        />
      </div>
    </div>
  )
}

export function AnalyticsPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null)
  const [operators, setOperators] = useState<OperatorStat[]>([])
  const [devices, setDevices] = useState<DeviceAnalytic[]>([])
  const [latency, setLatency] = useState<LatencyByMode[]>([])
  const [series, setSeries] = useState<{ t: string | null; v: number }[]>([])

  const refresh = useCallback(async () => {
    if (!token) return
    const [o, op, d, lat, ts] = await Promise.all([
      fetchAnalyticsOverview(token),
      fetchAnalyticsOperators(token),
      fetchAnalyticsDevices(token),
      fetchAnalyticsLatency(token),
      fetchAnalyticsTimeseries(token, 'sent', 24),
    ])
    setOverview(o)
    setOperators(op.results)
    setDevices(d.results)
    setLatency(lat.by_mode)
    setSeries(ts.points)
  }, [token])

  useEffect(() => {
    void refresh().catch(() => undefined)
  }, [refresh])

  const maxOp = Math.max(1, ...operators.map((o) => o.sent))
  const maxSeries = Math.max(1, ...series.map((p) => p.v))

  return (
    <div>
      <header className="page-header">
        <h1>{t('analytics.title')}</h1>
        <p>{t('analytics.subtitle')}</p>
      </header>

      <div className="stat-row">
        <div className="stat-tile">
          <div className="label">{t('analytics.sentToday')}</div>
          <div className="value">{overview?.messages.sent_today ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">{t('analytics.failedToday')}</div>
          <div className="value">{overview?.messages.failed_today ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">{t('analytics.avgLatency')}</div>
          <div className="value">
            {overview?.messages.avg_latency_ms_today != null
              ? `${Math.round(overview.messages.avg_latency_ms_today)}ms`
              : '—'}
          </div>
        </div>
      </div>

      <div className="panel-grid" style={{ display: 'grid', gap: 16, gridTemplateColumns: '1fr 1fr' }}>
        <section className="panel">
          <h2 style={{ fontSize: 16, marginBottom: 12 }}>{t('analytics.operators')}</h2>
          {operators.length ? (
            operators.map((row) => (
              <Bar
                key={row.operator}
                label={`${row.operator} · ${
                  row.avg_latency_ms != null
                    ? `${Math.round(row.avg_latency_ms)}ms`
                    : '—'
                }`}
                value={row.sent}
                max={maxOp}
              />
            ))
          ) : (
            <p className="muted-text">{t('analytics.empty')}</p>
          )}
        </section>

        <section className="panel">
          <h2 style={{ fontSize: 16, marginBottom: 12 }}>{t('analytics.latencyByMode')}</h2>
          {latency.length ? (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>{t('analytics.mode')}</th>
                    <th>{t('analytics.avgLatency')}</th>
                    <th>{t('analytics.count')}</th>
                  </tr>
                </thead>
                <tbody>
                  {latency.map((row) => (
                    <tr key={row.mode}>
                      <td>{row.mode}</td>
                      <td>
                        {row.avg_latency_ms != null
                          ? `${Math.round(row.avg_latency_ms)}ms`
                          : '—'}
                      </td>
                      <td>{row.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted-text">{t('analytics.empty')}</p>
          )}
        </section>
      </div>

      <section className="panel" style={{ marginTop: 16 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>{t('analytics.hourlySent')}</h2>
        {series.length ? (
          series.map((point) => (
            <Bar
              key={String(point.t)}
              label={point.t ? new Date(point.t).toLocaleString() : '—'}
              value={point.v}
              max={maxSeries}
            />
          ))
        ) : (
          <p className="muted-text">{t('analytics.empty')}</p>
        )}
      </section>

      <section className="panel" style={{ marginTop: 16 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>{t('analytics.devices')}</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('devices.colName')}</th>
                <th>{t('analytics.health')}</th>
                <th>{t('analytics.sent')}</th>
                <th>{t('analytics.failed')}</th>
                <th>{t('analytics.avgLatency')}</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((d) => (
                <tr key={d.device_id}>
                  <td>{d.name}</td>
                  <td>
                    {'★'.repeat(Math.max(1, Math.round(d.health_score / 20)))}{' '}
                    {d.health_score}
                  </td>
                  <td>{d.sent}</td>
                  <td>{d.failed}</td>
                  <td>
                    {d.avg_latency_ms != null
                      ? `${Math.round(d.avg_latency_ms)}ms`
                      : '—'}
                  </td>
                </tr>
              ))}
              {!devices.length ? (
                <tr>
                  <td colSpan={5}>{t('analytics.empty')}</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
