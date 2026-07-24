import { useTranslation } from 'react-i18next'
import type { Device } from '../../shared/api/devices'

type HealthMap = Record<string, unknown>

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function asBool(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let value = bytes / 1024
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unit]}`
}

function scoreTone(score: number): string {
  if (score >= 80) return 'good'
  if (score >= 50) return 'warn'
  return 'bad'
}

type Props = {
  device: Device
}

export function DeviceHealthSection({ device }: Props) {
  const { t } = useTranslation()
  const health = (device.health || {}) as HealthMap

  const battery = asNumber(health.battery)
  const charging = asBool(health.charging)
  const signal = asString(health.signal)
  const network = asString(health.network)
  const queueSize = asNumber(health.queue_size)
  const storageFree = asNumber(health.storage_free)
  const permissions = asRecord(health.permissions)
  const permissionEntries = Object.entries(permissions)
  const simsFromHealth = Array.isArray(health.sims) ? health.sims : []
  const sims =
    device.sims?.length > 0
      ? device.sims.map((s) => ({
          slot: s.slot_index,
          operator: s.operator,
          phone: s.phone_number,
          active: s.is_active,
        }))
      : simsFromHealth.map((raw) => {
          const sim = asRecord(raw)
          return {
            slot: asNumber(sim.slot_index) ?? asNumber(sim.slot) ?? 0,
            operator: asString(sim.operator) || '—',
            phone: asString(sim.phone_number) || asString(sim.number) || '—',
            active: true,
          }
        })

  const score = device.health_score ?? 0
  const hasAnyMetric =
    battery != null ||
    signal != null ||
    network != null ||
    queueSize != null ||
    storageFree != null ||
    permissionEntries.length > 0 ||
    sims.length > 0

  return (
    <section className="panel device-health" style={{ marginBottom: 24 }}>
      <div className="device-health-header">
        <h2 style={{ fontSize: 16, margin: 0 }}>{t('detail.health')}</h2>
        <div className={`health-score-badge health-score-${scoreTone(score)}`}>
          <span className="health-score-value">{score}</span>
          <span className="health-score-label">{t('detail.healthScore')}</span>
        </div>
      </div>

      {!hasAnyMetric ? (
        <p className="muted-text">{t('detail.healthEmpty')}</p>
      ) : (
        <>
          <div className="health-metrics">
            <article className="health-metric">
              <span className="label">{t('detail.battery')}</span>
              <span className="value">
                {battery != null ? `${battery}%` : '—'}
              </span>
              <span className="hint">
                {charging == null
                  ? t('detail.chargingUnknown')
                  : charging
                    ? t('detail.chargingYes')
                    : t('detail.chargingNo')}
              </span>
              {battery != null ? (
                <div className="health-bar" aria-hidden>
                  <div
                    className={`health-bar-fill ${
                      battery <= 20 ? 'bad' : battery <= 40 ? 'warn' : 'good'
                    }`}
                    style={{ width: `${Math.max(0, Math.min(100, battery))}%` }}
                  />
                </div>
              ) : null}
            </article>

            <article className="health-metric">
              <span className="label">{t('detail.signal')}</span>
              <span className="value health-signal">
                {signal ? t(`detail.signalValue.${signal}`, { defaultValue: signal }) : '—'}
              </span>
            </article>

            <article className="health-metric">
              <span className="label">{t('detail.network')}</span>
              <span className="value">
                {network ? t(`detail.networkValue.${network}`, { defaultValue: network }) : '—'}
              </span>
            </article>

            <article className="health-metric">
              <span className="label">{t('detail.queueSize')}</span>
              <span className="value">{queueSize != null ? queueSize : '—'}</span>
            </article>

            <article className="health-metric">
              <span className="label">{t('detail.storageFree')}</span>
              <span className="value">
                {storageFree != null ? formatBytes(storageFree) : '—'}
              </span>
            </article>

            <article className="health-metric">
              <span className="label">{t('detail.agentVersion')}</span>
              <span className="value health-version">
                {device.agent_version || '—'}
              </span>
            </article>
          </div>

          {permissionEntries.length > 0 ? (
            <div className="health-subsection">
              <h3 className="health-subheading">{t('detail.permissions')}</h3>
              <div className="health-chips">
                {permissionEntries.map(([key, value]) => {
                  const ok = value === true
                  return (
                    <span
                      key={key}
                      className={`health-chip ${ok ? 'ok' : 'off'}`}
                    >
                      {t(`detail.permission.${key}`, { defaultValue: key })}
                      {': '}
                      {ok ? t('detail.permGranted') : t('detail.permDenied')}
                    </span>
                  )
                })}
              </div>
            </div>
          ) : null}

          {sims.length > 0 ? (
            <div className="health-subsection">
              <h3 className="health-subheading">{t('detail.sims')}</h3>
              <div className="health-sim-list">
                {sims.map((sim) => (
                  <div key={`${sim.slot}-${sim.phone}`} className="health-sim">
                    <span className="health-sim-slot">
                      {t('detail.simSlot', { slot: sim.slot })}
                    </span>
                    <span className="health-sim-operator">{sim.operator || '—'}</span>
                    <span className="muted-text">{sim.phone || '—'}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </>
      )}
    </section>
  )
}
