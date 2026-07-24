import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { listDevices, type Device } from '../../shared/api/devices'
import {
  createRoutingRule,
  deleteRoutingRule,
  getRoutingConfig,
  listRoutingRules,
  updateRoutingConfig,
  updateRoutingRule,
  type RoutingConfig,
  type RoutingRule,
} from '../../shared/api/routing'
import {
  fetchRoutingSuggestions,
  type RoutingSuggestion,
} from '../../shared/api/ai'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'

const LB_OPTIONS = [
  'least_queue',
  'round_robin',
  'random',
  'priority',
  'weighted',
] as const

export function RoutingPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [rules, setRules] = useState<RoutingRule[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [config, setConfig] = useState<RoutingConfig | null>(null)
  const [suggestions, setSuggestions] = useState<RoutingSuggestion[]>([])
  const [error, setError] = useState<string | null>(null)

  const [name, setName] = useState('')
  const [priority, setPriority] = useState('100')
  const [prefix, setPrefix] = useState('+98912')
  const [actionType, setActionType] = useState('prefer_devices')
  const [deviceId, setDeviceId] = useState('')

  const refresh = useCallback(async () => {
    if (!token) return
    const [r, c, d] = await Promise.all([
      listRoutingRules(token),
      getRoutingConfig(token),
      listDevices(token),
    ])
    setRules(r.results)
    setConfig(c)
    setDevices(d.results.filter((x) => x.is_paired))
    if (!deviceId && d.results[0]) setDeviceId(d.results[0].id)
  }, [token, deviceId])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refresh, t])

  async function onCreateRule(event: FormEvent) {
    event.preventDefault()
    if (!token || !deviceId) return
    try {
      const action =
        actionType === 'force_device'
          ? { type: 'force_device', device_id: deviceId }
          : { type: 'prefer_devices', device_ids: [deviceId] }
      await createRoutingRule(token, {
        name,
        priority: Number(priority) || 100,
        match: prefix ? { to_prefix: [prefix] } : {},
        action,
        enabled: true,
      })
      setName('')
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function onSaveConfig(event: FormEvent) {
    event.preventDefault()
    if (!token || !config) return
    try {
      const updated = await updateRoutingConfig(token, config)
      setConfig(updated)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function toggleRule(rule: RoutingRule) {
    if (!token) return
    try {
      await updateRoutingRule(token, rule.id, { enabled: !rule.enabled })
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function removeRule(rule: RoutingRule) {
    if (!token) return
    try {
      await deleteRoutingRule(token, rule.id)
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function onSuggest() {
    if (!token) return
    try {
      const res = await fetchRoutingSuggestions(token)
      setSuggestions(res.results)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function applySuggestion(s: RoutingSuggestion) {
    if (!token) return
    try {
      await createRoutingRule(token, {
        name: s.name,
        priority: s.priority,
        match: s.match,
        action: s.action,
        enabled: true,
      })
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('routing.title')}</h1>
        <p>{t('routing.subtitle')}</p>
      </header>

      <section className="panel" style={{ marginBottom: 24 }}>
        <div className="toolbar">
          <Button type="button" variant="secondary" onClick={() => void onSuggest()}>
            {t('routing.aiSuggest')}
          </Button>
        </div>
        {suggestions.length ? (
          <div className="table-wrap" style={{ marginTop: 12 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('routing.ruleName')}</th>
                  <th>{t('routing.aiRationale')}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {suggestions.map((s) => (
                  <tr key={s.name + s.confidence}>
                    <td>
                      {s.name}
                      <div className="muted-text">
                        conf {Math.round(s.confidence * 100)}% · n={s.sample_size}
                      </div>
                    </td>
                    <td>{s.rationale}</td>
                    <td>
                      <button
                        type="button"
                        className="df-btn df-btn-ghost"
                        onClick={() => void applySuggestion(s)}
                      >
                        {t('routing.aiApply')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {config ? (
        <section className="panel" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, marginBottom: 12 }}>{t('routing.configTitle')}</h2>
          <form className="auth-form" onSubmit={(e) => void onSaveConfig(e)}>
            <div className="toolbar">
              <Field label={t('routing.lbStrategy')} htmlFor="lb">
                <select
                  id="lb"
                  className="df-input"
                  value={config.lb_strategy}
                  onChange={(e) =>
                    setConfig({ ...config, lb_strategy: e.target.value })
                  }
                >
                  {LB_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t('routing.rateMinute')} htmlFor="rlm">
                <TextInput
                  id="rlm"
                  type="number"
                  value={String(config.rate_limit_per_minute)}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      rate_limit_per_minute: Number(e.target.value) || 0,
                    })
                  }
                />
              </Field>
              <Field label={t('routing.rateHour')} htmlFor="rlh">
                <TextInput
                  id="rlh"
                  type="number"
                  value={String(config.rate_limit_per_hour)}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      rate_limit_per_hour: Number(e.target.value) || 0,
                    })
                  }
                />
              </Field>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={config.ha_enabled}
                  onChange={(e) =>
                    setConfig({ ...config, ha_enabled: e.target.checked })
                  }
                />
                {t('routing.haEnabled')}
              </label>
              <Field label={t('routing.otpWeight')} htmlFor="otpw">
                <TextInput
                  id="otpw"
                  type="number"
                  value={String(config.otp_queue_weight ?? 10)}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      otp_queue_weight: Number(e.target.value) || 0,
                    })
                  }
                />
              </Field>
              <Field label={t('routing.marketingWeight')} htmlFor="mkw">
                <TextInput
                  id="mkw"
                  type="number"
                  value={String(config.marketing_queue_weight ?? 1)}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      marketing_queue_weight: Number(e.target.value) || 0,
                    })
                  }
                />
              </Field>
              <Field label={t('routing.marketingJitter')} htmlFor="mkj">
                <TextInput
                  id="mkj"
                  type="number"
                  value={String(config.marketing_jitter_max_seconds ?? 15)}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      marketing_jitter_max_seconds: Number(e.target.value) || 0,
                    })
                  }
                />
              </Field>
              <Field label={t('routing.simQuota')} htmlFor="simq">
                <TextInput
                  id="simq"
                  type="number"
                  value={String(config.sim_daily_quota_default ?? 1000)}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      sim_daily_quota_default: Number(e.target.value) || 0,
                    })
                  }
                />
              </Field>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={config.adaptive_throttle_enabled ?? true}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      adaptive_throttle_enabled: e.target.checked,
                    })
                  }
                />
                {t('routing.adaptiveThrottle')}
              </label>
              <Button type="submit">{t('routing.saveConfig')}</Button>
            </div>
          </form>
        </section>
      ) : null}

      <section className="panel" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>{t('routing.createTitle')}</h2>
        <form className="auth-form" onSubmit={(e) => void onCreateRule(e)}>
          <div className="toolbar">
            <Field label={t('routing.ruleName')} htmlFor="rname">
              <TextInput
                id="rname"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </Field>
            <Field label={t('routing.priority')} htmlFor="rpri">
              <TextInput
                id="rpri"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
              />
            </Field>
            <Field label={t('routing.prefix')} htmlFor="rprefix">
              <TextInput
                id="rprefix"
                value={prefix}
                onChange={(e) => setPrefix(e.target.value)}
              />
            </Field>
            <Field label={t('routing.action')} htmlFor="raction">
              <select
                id="raction"
                className="df-input"
                value={actionType}
                onChange={(e) => setActionType(e.target.value)}
              >
                <option value="prefer_devices">{t('routing.prefer')}</option>
                <option value="force_device">{t('routing.force')}</option>
              </select>
            </Field>
            <Field label={t('routing.device')} htmlFor="rdev">
              <select
                id="rdev"
                className="df-input"
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
                required
              >
                {devices.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </Field>
            <Button type="submit">{t('routing.create')}</Button>
          </div>
        </form>
      </section>

      {error ? <div className="auth-error">{error}</div> : null}

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('routing.ruleName')}</th>
              <th>{t('routing.priority')}</th>
              <th>{t('routing.match')}</th>
              <th>{t('routing.action')}</th>
              <th>{t('routing.enabled')}</th>
              <th>{t('routing.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => (
              <tr key={rule.id}>
                <td>{rule.name}</td>
                <td>{rule.priority}</td>
                <td>
                  <code style={{ fontSize: 12 }}>{JSON.stringify(rule.match)}</code>
                </td>
                <td>
                  <code style={{ fontSize: 12 }}>{JSON.stringify(rule.action)}</code>
                </td>
                <td>{rule.enabled ? 'yes' : 'no'}</td>
                <td>
                  <button
                    type="button"
                    className="df-btn df-btn-ghost"
                    onClick={() => void toggleRule(rule)}
                  >
                    {rule.enabled ? t('routing.disable') : t('routing.enable')}
                  </button>
                  <button
                    type="button"
                    className="df-btn df-btn-ghost"
                    onClick={() => void removeRule(rule)}
                  >
                    {t('routing.delete')}
                  </button>
                </td>
              </tr>
            ))}
            {!rules.length ? (
              <tr>
                <td colSpan={6}>{t('routing.empty')}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
