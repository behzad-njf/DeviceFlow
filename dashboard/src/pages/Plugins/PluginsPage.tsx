import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import {
  installPlugin,
  listPlugins,
  updatePlugin,
  type PluginInfo,
} from '../../shared/api/extensibility'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'

export function PluginsPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [plugins, setPlugins] = useState<PluginInfo[]>([])
  const [webhookUrl, setWebhookUrl] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [apiVersion, setApiVersion] = useState('')

  const refresh = useCallback(async () => {
    if (!token) return
    const data = await listPlugins(token)
    setPlugins(data.results)
    setApiVersion(data.plugin_api_version)
  }, [token])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refresh, t])

  async function onInstall(plugin: PluginInfo, event: FormEvent) {
    event.preventDefault()
    if (!token) return
    try {
      const config =
        plugin.id === 'slack-notifier' && webhookUrl
          ? { webhook_url: webhookUrl }
          : plugin.config || {}
      await installPlugin(token, {
        plugin_id: plugin.id,
        config,
        enabled: true,
      })
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function toggle(plugin: PluginInfo) {
    if (!token || !plugin.installed) return
    try {
      await updatePlugin(token, plugin.id, { enabled: !plugin.enabled })
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('plugins.title')}</h1>
        <p>
          {t('plugins.subtitle')} {apiVersion ? `(API ${apiVersion})` : ''}
        </p>
      </header>
      {error ? <div className="auth-error">{error}</div> : null}
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('plugins.name')}</th>
              <th>{t('plugins.version')}</th>
              <th>{t('plugins.hooks')}</th>
              <th>{t('plugins.status')}</th>
              <th>{t('plugins.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {plugins.map((p) => (
              <tr key={p.id}>
                <td>
                  <strong>{p.name}</strong>
                  <div className="muted-text">{p.id}</div>
                </td>
                <td>{p.version}</td>
                <td>{(p.hooks || []).join(', ')}</td>
                <td>
                  {p.installed
                    ? p.enabled
                      ? t('plugins.enabled')
                      : t('plugins.disabled')
                    : t('plugins.available')}
                </td>
                <td>
                  {!p.installed ? (
                    <form
                      className="toolbar"
                      onSubmit={(e) => void onInstall(p, e)}
                      style={{ gap: 8 }}
                    >
                      {p.id === 'slack-notifier' ? (
                        <Field label={t('plugins.webhookUrl')} htmlFor={`wh-${p.id}`}>
                          <TextInput
                            id={`wh-${p.id}`}
                            value={webhookUrl}
                            onChange={(e) => setWebhookUrl(e.target.value)}
                            placeholder="https://hooks.slack.com/..."
                          />
                        </Field>
                      ) : null}
                      <Button type="submit">{t('plugins.install')}</Button>
                    </form>
                  ) : (
                    <button
                      type="button"
                      className="df-btn df-btn-ghost"
                      onClick={() => void toggle(p)}
                    >
                      {p.enabled ? t('plugins.disable') : t('plugins.enable')}
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!plugins.length ? (
              <tr>
                <td colSpan={5}>{t('plugins.empty')}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
