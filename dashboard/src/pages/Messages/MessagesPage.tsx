import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { listDevices, type Device } from '../../shared/api/devices'
import {
  cancelMessage,
  listInbound,
  listMessages,
  retryMessage,
  sendMessage,
  type InboundMessage,
  type Message,
} from '../../shared/api/messages'
import { listProjects, type Project } from '../../shared/api/projects'
import type { Contact } from '../../shared/api/phase6'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { ContactPicker } from '../../shared/ui/ContactPicker'
import { useAuthStore } from '../../features/auth/authStore'

export function MessagesPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [messages, setMessages] = useState<Message[]>([])
  const [inbound, setInbound] = useState<InboundMessage[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [to, setTo] = useState('')
  const [text, setText] = useState('')
  const [deviceId, setDeviceId] = useState('')
  const [projectSlug, setProjectSlug] = useState('')
  const [contactLabel, setContactLabel] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    if (!token) return
    const [msg, inbox, devs, projs] = await Promise.all([
      listMessages(token),
      listInbound(token),
      listDevices(token),
      listProjects(token),
    ])
    setMessages(msg.results)
    setInbound(inbox.results)
    setDevices(devs.results)
    setProjects(projs.results)
  }, [token])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
    const id = window.setInterval(() => {
      void refresh().catch(() => undefined)
    }, 4000)
    return () => window.clearInterval(id)
  }, [refresh, t])

  function onPickContact(contact: Contact | null) {
    if (!contact) {
      setContactLabel(null)
      return
    }
    setTo(contact.phone_number)
    setContactLabel(contact.name || contact.phone_number)
  }

  async function onSend(event: FormEvent) {
    event.preventDefault()
    if (!token) return
    setLoading(true)
    setError(null)
    setNotice(null)
    try {
      await sendMessage(token, {
        to,
        text,
        device: deviceId || undefined,
        project: projectSlug || undefined,
      })
      setText('')
      setNotice(t('messages.sentOk'))
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <header className="page-header page-header-split">
        <div>
          <h1>{t('messages.title')}</h1>
          <p>{t('messages.subtitle')}</p>
        </div>
        <Link className="df-btn df-btn-secondary" to="/bulk">
          {t('messages.openBulk')}
        </Link>
      </header>

      {error ? <div className="auth-error">{error}</div> : null}
      {notice ? <div className="auth-success">{notice}</div> : null}

      <section className="panel messages-send-panel">
        <h2 className="contacts-section-title">{t('messages.sendTitle')}</h2>
        <form className="auth-form" onSubmit={(e) => void onSend(e)}>
          <div className="messages-send-grid">
            <Field label={t('messages.pickContact')} htmlFor="contact-pick">
              {token ? (
                <ContactPicker token={token} value={to} onSelect={onPickContact} />
              ) : null}
              {contactLabel ? (
                <p className="muted-text">{t('messages.selectedContact', { name: contactLabel })}</p>
              ) : null}
            </Field>
            <Field label={t('messages.to')} htmlFor="to">
              <TextInput
                id="to"
                value={to}
                onChange={(e) => {
                  setTo(e.target.value)
                  setContactLabel(null)
                }}
                placeholder="+98912..."
                required
              />
            </Field>
            <Field label={t('messages.device')} htmlFor="device">
              <select
                id="device"
                className="df-input"
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
              >
                <option value="">{t('messages.anyDevice')}</option>
                {devices.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.status})
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t('messages.project')} htmlFor="project">
              <select
                id="project"
                className="df-input"
                value={projectSlug}
                onChange={(e) => setProjectSlug(e.target.value)}
              >
                <option value="">{t('messages.noProject')}</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.slug}>
                    {p.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field label={t('messages.text')} htmlFor="text">
            <textarea
              id="text"
              className="df-input"
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              required
            />
          </Field>
          <Button type="submit" disabled={loading}>
            {t('messages.send')}
          </Button>
        </form>
      </section>

      <div className="messages-columns">
        <section>
          <h2 className="contacts-section-title">{t('messages.outbound')}</h2>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('messages.colTime')}</th>
                  <th>{t('messages.colTo')}</th>
                  <th>{t('messages.colBody')}</th>
                  <th>{t('messages.colDevice')}</th>
                  <th>{t('messages.colStatus')}</th>
                  <th>{t('messages.colActions')}</th>
                </tr>
              </thead>
              <tbody>
                {messages.map((m) => (
                  <tr key={m.id}>
                    <td>{new Date(m.created_at).toLocaleString()}</td>
                    <td>{m.to_number}</td>
                    <td className="truncate">{m.body}</td>
                    <td>{m.device_name || '—'}</td>
                    <td>
                      <span className={`status-chip status-${m.status}`}>{m.status}</span>
                    </td>
                    <td className="row-actions">
                      {['failed', 'dead_letter', 'cancelled'].includes(m.status) ? (
                        <button
                          type="button"
                          className="df-btn df-btn-ghost"
                          onClick={() =>
                            token &&
                            void retryMessage(token, m.id)
                              .then(refresh)
                              .catch((err) =>
                                setError(
                                  err instanceof ApiError ? err.message : t('common.error'),
                                ),
                              )
                          }
                        >
                          {t('messages.retry')}
                        </button>
                      ) : null}
                      {['queued', 'assigned', 'retrying', 'sending'].includes(m.status) ? (
                        <button
                          type="button"
                          className="df-btn df-btn-ghost"
                          onClick={() =>
                            token &&
                            void cancelMessage(token, m.id)
                              .then(refresh)
                              .catch((err) =>
                                setError(
                                  err instanceof ApiError ? err.message : t('common.error'),
                                ),
                              )
                          }
                        >
                          {t('messages.cancel')}
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
                {!messages.length ? (
                  <tr>
                    <td colSpan={6}>{t('messages.empty')}</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="contacts-section-title">{t('messages.inbound')}</h2>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('messages.colTime')}</th>
                  <th>{t('messages.colFrom')}</th>
                  <th>{t('messages.colBody')}</th>
                  <th>{t('messages.colDevice')}</th>
                </tr>
              </thead>
              <tbody>
                {inbound.map((m) => (
                  <tr key={m.id}>
                    <td>{new Date(m.received_at).toLocaleString()}</td>
                    <td>{m.from_number}</td>
                    <td className="truncate">{m.body}</td>
                    <td>{m.device_name}</td>
                  </tr>
                ))}
                {!inbound.length ? (
                  <tr>
                    <td colSpan={4}>{t('messages.inboundEmpty')}</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}
