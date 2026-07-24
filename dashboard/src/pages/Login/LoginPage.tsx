import { useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { login, register } from '../../shared/api/auth'
import { ApiError } from '../../shared/api/client'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'

export function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const accessToken = useAuthStore((s) => s.accessToken)
  const setSession = useAuthStore((s) => s.setSession)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [tenantName, setTenantName] = useState('')
  const [tenantSlug, setTenantSlug] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const nextPath = (() => {
    const raw = searchParams.get('next') || '/'
    return raw.startsWith('/') && !raw.startsWith('//') ? raw : '/'
  })()

  if (accessToken) {
    return <Navigate to={nextPath} replace />
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const result =
        mode === 'login'
          ? await login({ email, password, tenant_slug: tenantSlug || undefined })
          : await register({
              email,
              password,
              name,
              tenant_name: tenantName,
              tenant_slug: tenantSlug || undefined,
              locale: 'en',
            })
      setSession({
        access: result.access,
        refresh: result.refresh,
        user: result.user,
        tenant: result.tenant,
        role: result.role,
      })
      navigate(nextPath, { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError(t('auth.error'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="brand">{t('app.name')}</div>
        <h1>{mode === 'login' ? t('auth.loginTitle') : t('auth.registerTitle')}</h1>
        {error ? <div className="auth-error">{error}</div> : null}
        <form className="auth-form" onSubmit={onSubmit}>
          {mode === 'register' ? (
            <>
              <Field label={t('auth.name')} htmlFor="name">
                <TextInput
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                />
              </Field>
              <Field label={t('auth.tenantName')} htmlFor="tenantName">
                <TextInput
                  id="tenantName"
                  value={tenantName}
                  onChange={(e) => setTenantName(e.target.value)}
                  required
                />
              </Field>
            </>
          ) : null}
          <Field label={t('auth.email')} htmlFor="email">
            <TextInput
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </Field>
          <Field label={t('auth.password')} htmlFor="password">
            <TextInput
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </Field>
          <Field label={t('auth.tenantSlug')} htmlFor="tenantSlug">
            <TextInput
              id="tenantSlug"
              value={tenantSlug}
              onChange={(e) => setTenantSlug(e.target.value)}
            />
          </Field>
          <Button type="submit" disabled={loading}>
            {mode === 'login' ? t('auth.submitLogin') : t('auth.submitRegister')}
          </Button>
        </form>
        <button
          type="button"
          className="auth-switch"
          onClick={() => {
            setMode((m) => (m === 'login' ? 'register' : 'login'))
            setError(null)
          }}
        >
          {mode === 'login' ? t('auth.switchToRegister') : t('auth.switchToLogin')}
        </button>
      </div>
    </div>
  )
}
