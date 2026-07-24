import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../features/auth/authStore'
import { useAlertStore } from '../features/alerts/alertStore'
import type { Locale, ThemeMode } from '../shared/lib/types'
import { dashboardSocket, type WsStatus } from '../shared/ws/client'

function resolveTheme(theme: ThemeMode): 'light' | 'dark' {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light'
  }
  return theme
}

export function AppShell() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const tenant = useAuthStore((s) => s.tenant)
  const accessToken = useAuthStore((s) => s.accessToken)
  const locale = useAuthStore((s) => s.locale)
  const theme = useAuthStore((s) => s.theme)
  const setLocale = useAuthStore((s) => s.setLocale)
  const setTheme = useAuthStore((s) => s.setTheme)
  const logout = useAuthStore((s) => s.logout)
  const alerts = useAlertStore((s) => s.alerts)
  const pushAlert = useAlertStore((s) => s.push)
  const dismiss = useAlertStore((s) => s.dismiss)
  const [wsStatus, setWsStatus] = useState<WsStatus>('disconnected')

  useEffect(() => {
    void i18n.changeLanguage(locale)
    document.documentElement.lang = locale
    document.documentElement.dir = locale === 'fa' ? 'rtl' : 'ltr'
  }, [locale, i18n])

  useEffect(() => {
    const applied = resolveTheme(theme)
    document.documentElement.setAttribute('data-theme', applied)
    if (theme !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => {
      document.documentElement.setAttribute(
        'data-theme',
        mq.matches ? 'dark' : 'light',
      )
    }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [theme])

  useEffect(() => {
    if (!accessToken) return
    dashboardSocket.connect(accessToken)
    const offStatus = dashboardSocket.onStatus(setWsStatus)
    const offEvent = dashboardSocket.onEvent((event) => {
      if (event.type === 'alert') {
        pushAlert({
          severity: String(event.payload?.severity || 'info'),
          title: String(event.payload?.title || 'Alert'),
          body: String(event.payload?.body || ''),
        })
      }
    })
    return () => {
      offStatus()
      offEvent()
      dashboardSocket.disconnect()
    }
  }, [accessToken, pushAlert])

  return (
    <div className="shell">
      <aside className="shell-sidebar">
        <div>
          <div className="shell-brand">{t('app.name')}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 4 }}>
            {tenant?.name || t('app.tagline')}
          </div>
        </div>
        <nav className="shell-nav">
          <NavLink to="/live">{t('nav.live')}</NavLink>
          <NavLink to="/inbox">{t('nav.inbox')}</NavLink>
          <NavLink to="/" end>
            {t('nav.overview')}
          </NavLink>
          <NavLink to="/analytics">{t('nav.analytics')}</NavLink>
          <NavLink to="/map">{t('nav.map')}</NavLink>
          <NavLink to="/devices">{t('nav.devices')}</NavLink>
          <NavLink to="/queues">{t('nav.queues')}</NavLink>
          <NavLink to="/messages">{t('nav.messages')}</NavLink>
          <NavLink to="/bulk">{t('nav.bulk')}</NavLink>
          <NavLink to="/contacts">{t('nav.contacts')}</NavLink>
          <NavLink to="/projects">{t('nav.projects')}</NavLink>
          <NavLink to="/routing">{t('nav.routing')}</NavLink>
          <NavLink to="/api-keys">{t('nav.apiKeys')}</NavLink>
          <NavLink to="/webhooks">{t('nav.webhooks')}</NavLink>
          <NavLink to="/automations">{t('nav.automations')}</NavLink>
          <NavLink to="/plugins">{t('nav.plugins')}</NavLink>
          <NavLink to="/notifications">{t('nav.notifications')}</NavLink>
          <NavLink to="/templates">{t('nav.templates')}</NavLink>
          <NavLink to="/users">{t('nav.users')}</NavLink>
          <NavLink to="/audit">{t('nav.audit')}</NavLink>
          <NavLink to="/playground">{t('nav.playground')}</NavLink>
        </nav>
        <div style={{ marginTop: 'auto', color: 'var(--text-muted)', fontSize: 12 }}>
          {user?.email}
        </div>
      </aside>
      <div className="shell-main">
        <header className="shell-topbar">
          <span className={`ws-pill ws-${wsStatus}`}>
            WS · {t(`ws.${wsStatus}`)}
          </span>
          <label>
            <span style={{ marginInlineEnd: 8 }}>{t('common.language')}</span>
            <select
              className="select-inline"
              value={locale}
              onChange={(e) => setLocale(e.target.value as Locale)}
            >
              <option value="en">English</option>
              <option value="fa">فارسی</option>
            </select>
          </label>
          <label>
            <span style={{ marginInlineEnd: 8 }}>{t('common.theme')}</span>
            <select
              className="select-inline"
              value={theme}
              onChange={(e) => setTheme(e.target.value as ThemeMode)}
            >
              <option value="system">{t('common.system')}</option>
              <option value="light">{t('common.light')}</option>
              <option value="dark">{t('common.dark')}</option>
            </select>
          </label>
          <button
            type="button"
            className="df-btn df-btn-ghost"
            onClick={() => {
              logout()
              navigate('/login', { replace: true })
            }}
          >
            {t('nav.logout')}
          </button>
        </header>
        {alerts[0] ? (
          <div className={`alert-banner severity-${alerts[0].severity}`}>
            <div>
              <strong>{alerts[0].title}</strong> — {alerts[0].body}
            </div>
            <button type="button" className="df-btn df-btn-ghost" onClick={() => dismiss(alerts[0].id)}>
              ×
            </button>
          </div>
        ) : null}
        <main className="shell-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
