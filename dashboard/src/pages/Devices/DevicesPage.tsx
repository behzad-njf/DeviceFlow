import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import {
  createPairingCode,
  listDevices,
  type Device,
  type PairingCodeResponse,
} from '../../shared/api/devices'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'
import { displayDeviceStatus } from '../../shared/lib/deviceStatus'

export function DevicesPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [devices, setDevices] = useState<Device[]>([])
  const [name, setName] = useState('')
  const [pairing, setPairing] = useState<PairingCodeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    if (!token) return
    const data = await listDevices(token)
    setDevices(data.results)
  }, [token])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
    const id = window.setInterval(() => {
      void refresh().catch(() => undefined)
    }, 15_000)
    return () => window.clearInterval(id)
  }, [refresh, t])

  async function onPair() {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const result = await createPairingCode(token, name)
      setPairing(result)
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('devices.title')}</h1>
        <p>{t('devices.subtitle')}</p>
      </header>

      <section className="panel" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>{t('devices.pairTitle')}</h2>
        <div className="toolbar">
          <Field label={t('devices.deviceName')} htmlFor="deviceName">
            <TextInput
              id="deviceName"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="office-phone"
            />
          </Field>
          <Button type="button" onClick={() => void onPair()} disabled={loading}>
            {t('devices.generateCode')}
          </Button>
        </div>
        {pairing ? (
          <div className="pairing-box">
            <div className="pairing-code">{pairing.code}</div>
            <p>
              {t('devices.pairingHint', {
                name: pairing.name,
                expires: new Date(pairing.expires_at).toLocaleString(),
              })}
            </p>
            <p className="muted-text">{t('devices.mockHint')}</p>
          </div>
        ) : null}
        {error ? <div className="auth-error" style={{ marginTop: 12 }}>{error}</div> : null}
      </section>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('devices.colName')}</th>
              <th>{t('devices.colStatus')}</th>
              <th>{t('devices.colHealth')}</th>
              <th>{t('devices.colBattery')}</th>
              <th>{t('devices.colSims')}</th>
              <th>{t('devices.colLastSeen')}</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => {
              const status = displayDeviceStatus(device)
              return (
              <tr key={device.id}>
                <td>
                  <Link to={`/devices/${device.id}`}>{device.name}</Link>
                </td>
                <td>
                  <span className={`status-chip status-${status}`}>
                    {status}
                  </span>
                </td>
                <td>
                  {'★'.repeat(Math.max(1, Math.round((device.health_score || 0) / 20)))}{' '}
                  {device.health_score}
                </td>
                <td>
                  {typeof device.health?.battery === 'number'
                    ? `${device.health.battery}%`
                    : t('overview.placeholder')}
                </td>
                <td>
                  {device.sims.length
                    ? device.sims
                        .map((s) => `SIM${s.slot_index} ${s.operator || ''}`.trim())
                        .join(', ')
                    : t('overview.placeholder')}
                </td>
                <td>
                  {device.last_seen_at
                    ? new Date(device.last_seen_at).toLocaleString()
                    : t('overview.placeholder')}
                </td>
              </tr>
              )
            })}
            {!devices.length ? (
              <tr>
                <td colSpan={6}>{t('devices.empty')}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
