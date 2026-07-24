import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import {
  createNotificationChannel,
  createNotificationRule,
  listNotificationChannels,
  listNotificationRules,
  type NotificationChannel,
  type NotificationRule,
} from '../../shared/api/extensibility'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'

export function NotificationsPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [channels, setChannels] = useState<NotificationChannel[]>([])
  const [rules, setRules] = useState<NotificationRule[]>([])
  const [channelType, setChannelType] = useState('telegram')
  const [configJson, setConfigJson] = useState('{"bot_token":"","chat_id":""}')
  const [ruleName, setRuleName] = useState('Offline → Telegram')
  const [ruleEvent, setRuleEvent] = useState('device.offline')
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!token) return
    const [c, r] = await Promise.all([
      listNotificationChannels(token),
      listNotificationRules(token),
    ])
    setChannels(c.results)
    setRules(r.results)
  }, [token])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refresh, t])

  async function onCreateChannel(event: FormEvent) {
    event.preventDefault()
    if (!token) return
    try {
      const config = JSON.parse(configJson || '{}') as Record<string, unknown>
      await createNotificationChannel(token, {
        channel_type: channelType,
        name: channelType,
        enabled: true,
        config,
      })
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function onCreateRule(event: FormEvent) {
    event.preventDefault()
    if (!token) return
    try {
      await createNotificationRule(token, {
        name: ruleName,
        event: ruleEvent,
        channels: [channelType, 'inapp'],
        cooldown_sec: 300,
      })
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('notifications.title')}</h1>
        <p>{t('notifications.subtitle')}</p>
      </header>
      {error ? <div className="auth-error">{error}</div> : null}

      <section className="panel" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>{t('notifications.channels')}</h2>
        <form className="auth-form" onSubmit={(e) => void onCreateChannel(e)}>
          <div className="toolbar">
            <Field label={t('notifications.type')} htmlFor="ntype">
              <select
                id="ntype"
                className="df-input"
                value={channelType}
                onChange={(e) => {
                  setChannelType(e.target.value)
                  if (e.target.value === 'telegram') {
                    setConfigJson('{"bot_token":"","chat_id":""}')
                  } else if (e.target.value === 'discord') {
                    setConfigJson('{"webhook_url":""}')
                  } else if (e.target.value === 'email') {
                    setConfigJson('{"to":["ops@example.com"]}')
                  }
                }}
              >
                <option value="telegram">telegram</option>
                <option value="discord">discord</option>
                <option value="email">email</option>
              </select>
            </Field>
            <Field label={t('notifications.config')} htmlFor="ncfg">
              <TextInput
                id="ncfg"
                value={configJson}
                onChange={(e) => setConfigJson(e.target.value)}
              />
            </Field>
            <Button type="submit">{t('notifications.addChannel')}</Button>
          </div>
        </form>
        <div className="table-wrap" style={{ marginTop: 16 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('notifications.type')}</th>
                <th>{t('notifications.enabled')}</th>
                <th>{t('notifications.config')}</th>
              </tr>
            </thead>
            <tbody>
              {channels.map((c) => (
                <tr key={c.id}>
                  <td>{c.channel_type}</td>
                  <td>{c.enabled ? 'yes' : 'no'}</td>
                  <td>
                    <code style={{ fontSize: 12 }}>{JSON.stringify(c.config)}</code>
                  </td>
                </tr>
              ))}
              {!channels.length ? (
                <tr>
                  <td colSpan={3}>{t('notifications.emptyChannels')}</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>{t('notifications.rules')}</h2>
        <form className="auth-form" onSubmit={(e) => void onCreateRule(e)}>
          <div className="toolbar">
            <Field label={t('notifications.ruleName')} htmlFor="rname">
              <TextInput
                id="rname"
                value={ruleName}
                onChange={(e) => setRuleName(e.target.value)}
                required
              />
            </Field>
            <Field label={t('notifications.event')} htmlFor="revent">
              <TextInput
                id="revent"
                value={ruleEvent}
                onChange={(e) => setRuleEvent(e.target.value)}
                required
              />
            </Field>
            <Button type="submit">{t('notifications.addRule')}</Button>
          </div>
        </form>
        <div className="table-wrap" style={{ marginTop: 16 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('notifications.ruleName')}</th>
                <th>{t('notifications.event')}</th>
                <th>{t('notifications.channels')}</th>
                <th>{t('notifications.cooldown')}</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td>{r.event}</td>
                  <td>{(r.channels || []).join(', ')}</td>
                  <td>{r.cooldown_sec}s</td>
                </tr>
              ))}
              {!rules.length ? (
                <tr>
                  <td colSpan={4}>{t('notifications.emptyRules')}</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
