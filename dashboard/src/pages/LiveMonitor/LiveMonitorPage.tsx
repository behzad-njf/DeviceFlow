import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { listDevices, type Device } from '../../shared/api/devices'
import { fetchAnalyticsOverview, type AnalyticsOverview } from '../../shared/api/ops'
import { useAuthStore } from '../../features/auth/authStore'
import { dashboardSocket } from '../../shared/ws/client'
import {
  applyDeviceUpdate,
  displayDeviceStatus,
} from '../../shared/lib/deviceStatus'

export function LiveMonitorPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [devices, setDevices] = useState<Device[]>([])
  const [stats, setStats] = useState<AnalyticsOverview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [, setTick] = useState(0)

  const refresh = useCallback(async () => {
    if (!token) return
    const [devs, overview] = await Promise.all([
      listDevices(token),
      fetchAnalyticsOverview(token),
    ])
    setDevices(devs.results.filter((d) => d.status !== 'disabled'))
    setStats(overview)
  }, [token])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
    const id = window.setInterval(() => {
      void refresh().catch(() => undefined)
    }, 30_000)
    return () => window.clearInterval(id)
  }, [refresh, t])

  useEffect(() => {
    const timer = window.setInterval(() => setTick((n) => n + 1), 10_000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    return dashboardSocket.onEvent((event) => {
      if (event.type !== 'device.updated' && event.type !== 'device.health') return
      const payload = event.payload || {}
      const deviceId = String(payload.id || payload.device_id || '')
      if (!deviceId) return
      setDevices((prev) =>
        prev.map((d) => (d.id === deviceId ? applyDeviceUpdate(d, payload) : d)),
      )
    })
  }, [])

  const onlineCount = devices.filter((d) => displayDeviceStatus(d) === 'online').length

  return (
    <div>
      <header className="page-header">
        <h1>{t('live.title')}</h1>
        <p>{t('live.subtitle')}</p>
      </header>

      {error ? <div className="auth-error">{error}</div> : null}

      <div className="stat-row">
        <div className="stat-tile">
          <div className="label">{t('live.online')}</div>
          <div className="value">{onlineCount || stats?.devices.online || '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">{t('overview.statsSent')}</div>
          <div className="value">{stats?.messages.sent_today ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">{t('overview.statsQueue')}</div>
          <div className="value">{stats?.messages.queue_depth ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">{t('live.failedToday')}</div>
          <div className="value">{stats?.messages.failed_today ?? '—'}</div>
        </div>
      </div>

      <div className="device-grid">
        {devices.map((device) => {
          const status = displayDeviceStatus(device)
          return (
            <Link key={device.id} to={`/devices/${device.id}`} className="device-card">
              <div className="device-card-head">
                <strong>{device.name}</strong>
                <span className={`status-chip status-${status}`}>{status}</span>
              </div>
              <div className="muted-text">
                {typeof device.health?.battery === 'number'
                  ? `${t('devices.colBattery')}: ${device.health.battery}%`
                  : t('overview.placeholder')}
              </div>
              <div className="muted-text">
                {device.sims.length
                  ? device.sims.map((s) => `SIM${s.slot_index} ${s.operator}`).join(' · ')
                  : t('overview.placeholder')}
              </div>
              <div className="muted-text">
                {device.last_seen_at
                  ? new Date(device.last_seen_at).toLocaleTimeString()
                  : t('overview.placeholder')}
              </div>
            </Link>
          )
        })}
        {!devices.length ? <div className="panel">{t('live.empty')}</div> : null}
      </div>
    </div>
  )
}
