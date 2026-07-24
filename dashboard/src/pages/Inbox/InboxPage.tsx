import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import {
  getConversation,
  listConversations,
  type Conversation,
} from '../../shared/api/phase6'
import { fetchInboxDraft } from '../../shared/api/ai'
import { sendMessage } from '../../shared/api/messages'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'

export function InboxPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [items, setItems] = useState<Conversation[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [selectedPhone, setSelectedPhone] = useState('')
  const [thread, setThread] = useState<
    Array<{ direction: string; at: string; message: Record<string, unknown> }>
  >([])
  const [draft, setDraft] = useState('')
  const [draftNote, setDraftNote] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(async () => {
    if (!token) return
    const res = await listConversations(token)
    setItems(res.results)
  }, [token])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refresh, t])

  async function openThread(c: Conversation) {
    if (!token) return
    setSelected(c.id)
    setSelectedPhone(c.phone_number)
    setDraft('')
    setDraftNote('')
    try {
      const res = await getConversation(token, c.id)
      setThread(res.messages)
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  async function onSuggest() {
    if (!token || !selected) return
    setBusy(true)
    try {
      const res = await fetchInboxDraft(token, selected)
      setDraft(res.draft)
      setDraftNote(`${res.source}: ${res.note}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  async function onSend() {
    if (!token || !selectedPhone || !draft.trim()) return
    setBusy(true)
    try {
      await sendMessage(token, { to: selectedPhone, text: draft.trim() })
      setDraft('')
      setDraftNote('')
      const res = await getConversation(token, selected!)
      setThread(res.messages)
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('inbox.title')}</h1>
        <p>{t('inbox.subtitle')}</p>
      </header>
      {error ? <div className="auth-error">{error}</div> : null}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(240px, 1fr) 2fr', gap: 16 }}>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('inbox.phone')}</th>
                <th>{t('inbox.preview')}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id}>
                  <td>
                    {c.contact_name || c.phone_number}
                    {c.unread_count ? ` (${c.unread_count})` : ''}
                  </td>
                  <td>{c.last_preview}</td>
                  <td>
                    <button
                      type="button"
                      className="df-btn df-btn-ghost"
                      onClick={() => void openThread(c)}
                    >
                      {t('inbox.open')}
                    </button>
                  </td>
                </tr>
              ))}
              {!items.length ? (
                <tr>
                  <td colSpan={3}>{t('inbox.empty')}</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        <section className="panel">
          <h2 style={{ fontSize: 16, marginBottom: 12 }}>
            {selected ? t('inbox.thread') : t('inbox.select')}
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 420, overflow: 'auto' }}>
            {thread.map((ev, idx) => (
              <div
                key={`${ev.at}-${idx}`}
                style={{
                  alignSelf: ev.direction === 'outbound' ? 'flex-end' : 'flex-start',
                  maxWidth: '80%',
                  padding: '8px 12px',
                  borderRadius: 8,
                  background:
                    ev.direction === 'outbound'
                      ? 'var(--accent-soft, #dbeafe)'
                      : 'var(--surface-2, #f3f4f6)',
                }}
              >
                <div style={{ fontSize: 11, opacity: 0.7 }}>{ev.direction} · {ev.at}</div>
                <div>{String(ev.message.body || '')}</div>
              </div>
            ))}
          </div>
          {selected ? (
            <div style={{ marginTop: 16 }}>
              <Field label={t('inbox.reply')} htmlFor="draft">
                <TextInput
                  id="draft"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder={t('inbox.replyPlaceholder')}
                />
              </Field>
              {draftNote ? <p className="muted-text">{draftNote}</p> : null}
              <div className="toolbar" style={{ marginTop: 8 }}>
                <Button type="button" variant="secondary" disabled={busy} onClick={() => void onSuggest()}>
                  {t('inbox.suggest')}
                </Button>
                <Button type="button" disabled={busy || !draft.trim()} onClick={() => void onSend()}>
                  {t('inbox.send')}
                </Button>
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  )
}
