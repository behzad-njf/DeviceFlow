import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import type { Device } from '../../shared/api/devices'
import {
  fetchDevice,
  fetchDeviceCommand,
  fetchDeviceEvents,
  sendDeviceCommand,
  type DeviceEvent,
  type EventsPagination,
} from '../../shared/api/ops'
import { listAgentReleases, type AgentRelease } from '../../shared/api/extensibility'
import { Button } from '../../shared/ui/Form'
import {
  IconChip,
  IconHealth,
  IconLogs,
  IconOta,
  IconRefresh,
  IconSim,
  IconSync,
  IconTrash,
  IconUssd,
} from '../../shared/ui/Icons'
import { useAuthStore } from '../../features/auth/authStore'
import { dashboardSocket } from '../../shared/ws/client'
import {
  applyDeviceUpdate,
  displayDeviceStatus,
} from '../../shared/lib/deviceStatus'
import { DeviceHealthSection } from './DeviceHealthSection'
import { DeviceTimelineSection } from './DeviceTimelineSection'
import { OtaModal } from './OtaModal'
import { SetDialerCodeModal } from './SetDialerCodeModal'
import { SetPasscodeModal } from './SetPasscodeModal'
import { UssdModal } from './UssdModal'

const COMMANDS = [
  { id: 'restart_agent', Icon: IconRefresh },
  { id: 'sync', Icon: IconSync },
  { id: 'clear_queue', Icon: IconTrash },
  { id: 'refresh_sim', Icon: IconSim },
  { id: 'enable_logs', Icon: IconLogs },
] as const

const SECURITY_COMMANDS = [
  'hide_launcher',
  'show_launcher',
  'lock_ui',
  'unlock_ui',
  'clear_passcode',
] as const

const SECURITY_META_BOOL_KEYS = ['launcher_hidden', 'ui_locked', 'passcode_set'] as const

const TIMELINE_REFRESH_TYPES = new Set([
  'device.offline',
  'device.online',
  'device.paired',
  'command.created',
  'command.acked',
  'permission.revoked',
])

const PAGE_SIZE = 15

function metaFlag(meta: Record<string, unknown> | undefined, key: string): boolean {
  return Boolean(meta?.[key])
}

function applySecurityResultMeta(
  prev: Device,
  result: Record<string, unknown> | undefined,
): Device {
  if (!result) return prev
  const nextMeta = { ...(prev.meta || {}) }
  let changed = false
  for (const key of SECURITY_META_BOOL_KEYS) {
    if (!(key in result)) continue
    const value = Boolean(result[key])
    if (nextMeta[key] !== value) {
      nextMeta[key] = value
      changed = true
    }
  }
  if (typeof result.dialer_code === 'string' && /^\d{3,8}$/.test(result.dialer_code)) {
    if (nextMeta.dialer_code !== result.dialer_code) {
      nextMeta.dialer_code = result.dialer_code
      changed = true
    }
  }
  return changed ? { ...prev, meta: nextMeta } : prev
}

async function waitForCommandAck(
  token: string,
  deviceId: string,
  commandId: string,
  timeoutMs = 15_000,
) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    const cmd = await fetchDeviceCommand(token, deviceId, commandId)
    if (cmd.status === 'acked' || cmd.status === 'failed') return cmd
    await new Promise((r) => setTimeout(r, 500))
  }
  return null
}

export function DeviceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [device, setDevice] = useState<Device | null>(null)
  const [events, setEvents] = useState<DeviceEvent[]>([])
  const [pagination, setPagination] = useState<EventsPagination | null>(null)
  const [releases, setReleases] = useState<AgentRelease[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [timelineLoading, setTimelineLoading] = useState(false)
  const [ussdOpen, setUssdOpen] = useState(false)
  const [otaOpen, setOtaOpen] = useState(false)
  const [passcodeOpen, setPasscodeOpen] = useState(false)
  const [dialerOpen, setDialerOpen] = useState(false)
  const [, setTick] = useState(0)

  const refreshDeviceAndReleases = useCallback(async () => {
    if (!token || !id) return
    const [d, r] = await Promise.all([fetchDevice(token, id), listAgentReleases(token)])
    setDevice(d)
    setReleases(r.results)
  }, [token, id])

  const refreshTimeline = useCallback(
    async (nextPage = 1) => {
      if (!token || !id) return
      setTimelineLoading(true)
      try {
        const e = await fetchDeviceEvents(token, id, {
          page: nextPage,
          pageSize: PAGE_SIZE,
        })
        setEvents(e.results)
        setPagination(e.pagination)
      } finally {
        setTimelineLoading(false)
      }
    },
    [token, id],
  )

  const refreshAll = useCallback(async () => {
    await Promise.all([refreshDeviceAndReleases(), refreshTimeline(1)])
  }, [refreshDeviceAndReleases, refreshTimeline])

  useEffect(() => {
    void refreshAll().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refreshAll, t])

  useEffect(() => {
    const timer = window.setInterval(() => setTick((n) => n + 1), 10_000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    return dashboardSocket.onEvent((event) => {
      if (!id) return
      const payload = event.payload || {}
      const eventDeviceId = String(payload.id || payload.device_id || '')
      if (eventDeviceId && eventDeviceId !== id) return

      if (event.type === 'device.updated' || event.type === 'device.health') {
        setDevice((prev) => (prev ? applyDeviceUpdate(prev, payload) : prev))
        return
      }

      if (TIMELINE_REFRESH_TYPES.has(event.type) || event.type.startsWith('sms.')) {
        void refreshTimeline(1).catch(() => undefined)
        if (event.type === 'command.acked') {
          const result =
            payload.result && typeof payload.result === 'object'
              ? (payload.result as Record<string, unknown>)
              : undefined
          setDevice((prev) => (prev ? applySecurityResultMeta(prev, result) : prev))
          void refreshDeviceAndReleases().catch(() => undefined)
        }
        if (event.type === 'device.offline' || event.type === 'device.online') {
          setDevice((prev) =>
            prev
              ? {
                  ...prev,
                  status: event.type === 'device.offline' ? 'offline' : 'online',
                }
              : prev,
          )
        }
      }
    })
  }, [id, refreshDeviceAndReleases, refreshTimeline])

  async function runCommand(command: string) {
    if (!token || !id) return
    setBusy(true)
    setError(null)
    try {
      const created = await sendDeviceCommand(token, id, command)
      await refreshTimeline(1)
      if (SECURITY_COMMANDS.includes(command as (typeof SECURITY_COMMANDS)[number]) || command === 'set_passcode' || command === 'set_dialer_code') {
        const finished = await waitForCommandAck(token, id, created.id)
        if (finished?.result) {
          setDevice((prev) =>
            prev ? applySecurityResultMeta(prev, finished.result as Record<string, unknown>) : prev,
          )
        }
        await refreshDeviceAndReleases()
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  if (!device) {
    return <div className="panel">{error || t('common.loading')}</div>
  }

  const shownStatus = displayDeviceStatus(device)
  const caps = device.capabilities || []
  const meta = device.meta || {}
  const launcherHidden = metaFlag(meta, 'launcher_hidden')
  const uiLocked = metaFlag(meta, 'ui_locked')
  const passcodeSet = metaFlag(meta, 'passcode_set')
  const dialerCode =
    typeof meta.dialer_code === 'string' && /^\d{3,8}$/.test(meta.dialer_code)
      ? meta.dialer_code
      : '3323'
  const ussdSims =
    device.sims?.length > 0
      ? device.sims
      : Array.isArray(device.health?.sims)
        ? (device.health.sims as Array<Record<string, unknown>>).map((s, i) => ({
            id: String(s.id || `health-${s.slot_index ?? i}`),
            slot_index: Number(s.slot_index ?? i + 1),
            operator: String(s.operator || ''),
            phone_number: String(s.phone_number || ''),
            is_active: true,
          }))
        : []

  return (
    <div>
      <header className="device-hero">
        <p className="device-hero-crumb">
          <Link to="/live">{t('live.title')}</Link>
          <span aria-hidden> / </span>
          <span>{device.name}</span>
        </p>
        <div className="device-hero-main">
          <div>
            <h1>{device.name}</h1>
            <div className="device-hero-meta">
              <span className={`status-chip status-${shownStatus}`}>{shownStatus}</span>
              <span className="device-meta-pill">
                <IconHealth size={14} />
                {t('detail.health')}: {device.health_score}
              </span>
              <span className="device-meta-pill muted-text">
                {t('detail.agentVersion')}: {device.agent_version || '—'}
              </span>
            </div>
          </div>
        </div>
        <div className="device-caps">
          <span className="device-caps-label">
            <IconChip size={14} />
            {t('detail.capabilities')}
          </span>
          <div className="device-caps-list">
            {caps.length ? (
              caps.map((cap) => (
                <span key={cap} className="cap-chip">
                  {t(`detail.cap.${cap}`, { defaultValue: cap })}
                </span>
              ))
            ) : (
              <span className="muted-text">{t('overview.placeholder')}</span>
            )}
          </div>
        </div>
      </header>

      {error ? <div className="auth-error">{error}</div> : null}

      <section className="panel" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>{t('detail.commands')}</h2>
        <div className="command-grid">
          {COMMANDS.map(({ id: cmd, Icon }) => (
            <Button
              key={cmd}
              type="button"
              variant="secondary"
              className="command-btn"
              disabled={busy}
              onClick={() => void runCommand(cmd)}
            >
              <Icon size={16} />
              {t(`detail.cmd.${cmd}`)}
            </Button>
          ))}
          <Button
            type="button"
            variant="secondary"
            className="command-btn"
            disabled={busy}
            onClick={() => setUssdOpen(true)}
          >
            <IconUssd size={16} />
            {t('detail.runUssd')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            className="command-btn"
            disabled={busy}
            onClick={() => setOtaOpen(true)}
          >
            <IconOta size={16} />
            {t('detail.ota')}
          </Button>
        </div>
      </section>

      <section className="panel" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>{t('detail.securityTitle')}</h2>
        <p className="muted-text" style={{ marginTop: 0, marginBottom: 12 }}>
          {t('detail.securityHint')}
        </p>
        <div className="security-status-grid">
          <div className="security-status-card">
            <span className="security-status-label">{t('detail.securityStatusLauncher')}</span>
            <span className={`security-status-value ${launcherHidden ? 'is-on' : 'is-off'}`}>
              {launcherHidden ? t('detail.securityHidden') : t('detail.securityVisible')}
            </span>
          </div>
          <div className="security-status-card">
            <span className="security-status-label">{t('detail.securityStatusLock')}</span>
            <span className={`security-status-value ${uiLocked ? 'is-on' : 'is-off'}`}>
              {uiLocked ? t('detail.securityLocked') : t('detail.securityUnlocked')}
            </span>
          </div>
          <div className="security-status-card">
            <span className="security-status-label">{t('detail.securityStatusPasscode')}</span>
            <span className={`security-status-value ${passcodeSet ? 'is-on' : 'is-off'}`}>
              {passcodeSet ? t('detail.securityPasscodeOn') : t('detail.securityPasscodeOff')}
            </span>
          </div>
          <div className="security-status-card">
            <span className="security-status-label">{t('detail.securityStatusDialer')}</span>
            <span className="security-status-value is-off">
              {t('detail.securityDialerFormat', { code: dialerCode })}
            </span>
          </div>
        </div>
        <div className="command-grid">
          {SECURITY_COMMANDS.map((cmd) => (
            <Button
              key={cmd}
              type="button"
              variant="secondary"
              className="command-btn"
              disabled={busy}
              onClick={() => void runCommand(cmd)}
            >
              {t(`detail.cmd.${cmd}`)}
            </Button>
          ))}
          <Button
            type="button"
            variant="secondary"
            className="command-btn"
            disabled={busy}
            onClick={() => setPasscodeOpen(true)}
          >
            {t('detail.securitySetPasscode')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            className="command-btn"
            disabled={busy}
            onClick={() => setDialerOpen(true)}
          >
            {t('detail.securitySetDialerCode')}
          </Button>
        </div>
      </section>

      <DeviceHealthSection device={device} />

      <DeviceTimelineSection
        events={events}
        pagination={pagination}
        loading={timelineLoading}
        onPageChange={(next) => {
          void refreshTimeline(next).catch(() => undefined)
        }}
      />

      {token && id ? (
        <>
          <UssdModal
            open={ussdOpen}
            onClose={() => setUssdOpen(false)}
            token={token}
            deviceId={id}
            sims={ussdSims}
            onFinished={() => {
              void refreshTimeline(1).catch(() => undefined)
            }}
          />
          <OtaModal
            open={otaOpen}
            onClose={() => setOtaOpen(false)}
            token={token}
            deviceId={id}
            releases={releases}
            onChanged={() => {
              void refreshDeviceAndReleases().catch(() => undefined)
              void refreshTimeline(1).catch(() => undefined)
            }}
          />
          <SetPasscodeModal
            open={passcodeOpen}
            onClose={() => setPasscodeOpen(false)}
            token={token}
            deviceId={id}
            onFinished={(result) => {
              setDevice((prev) => (prev ? applySecurityResultMeta(prev, result) : prev))
              void refreshTimeline(1).catch(() => undefined)
              void refreshDeviceAndReleases().catch(() => undefined)
            }}
          />
          <SetDialerCodeModal
            open={dialerOpen}
            onClose={() => setDialerOpen(false)}
            token={token}
            deviceId={id}
            currentCode={dialerCode}
            onFinished={(result) => {
              setDevice((prev) => (prev ? applySecurityResultMeta(prev, result) : prev))
              void refreshTimeline(1).catch(() => undefined)
              void refreshDeviceAndReleases().catch(() => undefined)
            }}
          />
        </>
      ) : null}
    </div>
  )
}
