import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import {
  inviteUser,
  listUsers,
  updateMembership,
  type Membership,
} from '../../shared/api/enterprise'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'

const ROLES = ['admin', 'developer', 'operator', 'viewer']

export function UsersPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [users, setUsers] = useState<Membership[]>([])
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('viewer')
  const [inviteToken, setInviteToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!token) return
    const res = await listUsers(token)
    setUsers(res.results)
  }, [token])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refresh, t])

  async function onInvite(event: FormEvent) {
    event.preventDefault()
    if (!token) return
    try {
      const created = await inviteUser(token, { email, role })
      setInviteToken(created.token || null)
      setEmail('')
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('users.title')}</h1>
        <p>{t('users.subtitle')}</p>
      </header>

      <section className="panel" style={{ marginBottom: 24 }}>
        <form className="auth-form" onSubmit={(e) => void onInvite(e)}>
          <div className="toolbar">
            <Field label={t('users.email')} htmlFor="u-email">
              <TextInput
                id="u-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </Field>
            <Field label={t('users.role')} htmlFor="u-role">
              <select
                id="u-role"
                className="df-input"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </Field>
            <Button type="submit">{t('users.invite')}</Button>
          </div>
        </form>
        {inviteToken ? (
          <div className="auth-error" style={{ marginTop: 12 }}>
            {t('users.tokenOnce')}: <code>{inviteToken}</code>
          </div>
        ) : null}
      </section>

      {error ? <div className="auth-error">{error}</div> : null}

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('users.email')}</th>
              <th>{t('users.name')}</th>
              <th>{t('users.role')}</th>
              <th>{t('users.active')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td>{u.name}</td>
                <td>
                  <select
                    className="df-input"
                    value={u.role}
                    onChange={(e) =>
                      void updateMembership(token!, u.id, { role: e.target.value }).then(
                        () => refresh(),
                      )
                    }
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td>{u.is_active ? 'yes' : 'no'}</td>
                <td>
                  <button
                    type="button"
                    className="df-btn df-btn-ghost"
                    onClick={() =>
                      void updateMembership(token!, u.id, {
                        is_active: !u.is_active,
                      }).then(() => refresh())
                    }
                  >
                    {u.is_active ? t('users.deactivate') : t('users.activate')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
