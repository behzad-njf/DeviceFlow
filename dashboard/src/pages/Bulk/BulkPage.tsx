import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { listProjects, type Project } from '../../shared/api/projects'
import {
  createExport,
  getExport,
  listBulkCampaigns,
  listContacts,
  sendBulk,
  type BulkCampaign,
  type Contact,
  type ExportJob,
} from '../../shared/api/phase6'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'
import { dashboardSocket } from '../../shared/ws/client'

type Mode = 'contacts' | 'csv'

function renderTemplate(template: string, contact: Contact) {
  return template
    .replaceAll('{{name}}', contact.name || contact.phone_number)
    .replaceAll('{{phone}}', contact.phone_number)
}

export function BulkPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState('')
  const [mode, setMode] = useState<Mode>('contacts')
  const [csv, setCsv] = useState('to,text\n+989121000001,Hello one\n+989121000002,Hello two')
  const [campaignName, setCampaignName] = useState('Dashboard campaign')
  const [template, setTemplate] = useState('Hi {{name}}, …')
  const [contacts, setContacts] = useState<Contact[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [contactQuery, setContactQuery] = useState('')
  const [campaigns, setCampaigns] = useState<BulkCampaign[]>([])
  const [exports, setExports] = useState<ExportJob[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const filteredContacts = useMemo(() => {
    const q = contactQuery.trim().toLowerCase()
    if (!q) return contacts
    return contacts.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.phone_number.toLowerCase().includes(q),
    )
  }, [contacts, contactQuery])

  const refresh = useCallback(async () => {
    if (!token) return
    const [p, c, contactsRes] = await Promise.all([
      listProjects(token),
      listBulkCampaigns(token),
      listContacts(token),
    ])
    setProjects(p.results)
    if (!projectId && p.results[0]) setProjectId(p.results[0].slug)
    setCampaigns(c.results)
    setContacts(contactsRes.results.filter((x) => !x.is_blacklisted))
  }, [token, projectId])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refresh, t])

  useEffect(() => {
    return dashboardSocket.onEvent((event) => {
      if (event.type === 'bulk.progress') {
        void refresh()
      }
    })
  }, [refresh])

  function toggleContact(id: string, checked: boolean) {
    setSelectedIds((prev) =>
      checked ? [...prev, id] : prev.filter((x) => x !== id),
    )
  }

  async function onBulk(event: FormEvent) {
    event.preventDefault()
    if (!token) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      let messages: Array<{ to: string; text: string }> = []
      if (mode === 'csv') {
        const lines = csv.trim().split('\n').slice(1)
        messages = lines
          .map((line) => {
            const [to, ...rest] = line.split(',')
            return { to: to.trim(), text: rest.join(',').trim() }
          })
          .filter((m) => m.to)
      } else {
        const picked = contacts.filter((c) => selectedIds.includes(c.id))
        if (!picked.length) {
          setError(t('bulk.noContactsSelected'))
          setBusy(false)
          return
        }
        if (!template.trim()) {
          setError(t('bulk.templateRequired'))
          setBusy(false)
          return
        }
        messages = picked.map((c) => ({
          to: c.phone_number,
          text: renderTemplate(template, c),
        }))
      }
      await sendBulk(token, {
        project: projectId || undefined,
        name: campaignName || 'Dashboard campaign',
        messages,
      })
      setNotice(t('bulk.started', { count: messages.length }))
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  async function onExport() {
    if (!token) return
    try {
      const job = await createExport(token, { type: 'messages', format: 'json' })
      const ready = await getExport(token, job.id)
      setExports((prev) => [ready, ...prev])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  return (
    <div>
      <header className="page-header page-header-split">
        <div>
          <h1>{t('bulk.title')}</h1>
          <p>{t('bulk.subtitle')}</p>
        </div>
        <Link className="df-btn df-btn-secondary" to="/messages">
          {t('bulk.openMessages')}
        </Link>
      </header>

      {error ? <div className="auth-error">{error}</div> : null}
      {notice ? <div className="auth-success">{notice}</div> : null}

      <section className="panel" style={{ marginBottom: 24 }}>
        <div className="bulk-mode-tabs">
          <button
            type="button"
            className={`bulk-mode-tab ${mode === 'contacts' ? 'is-active' : ''}`}
            onClick={() => setMode('contacts')}
          >
            {t('bulk.modeContacts')}
          </button>
          <button
            type="button"
            className={`bulk-mode-tab ${mode === 'csv' ? 'is-active' : ''}`}
            onClick={() => setMode('csv')}
          >
            {t('bulk.modeCsv')}
          </button>
        </div>

        <form className="auth-form" onSubmit={(e) => void onBulk(e)}>
          <div className="toolbar" style={{ marginBottom: 12 }}>
            <Field label={t('bulk.project')} htmlFor="b-project">
              <select
                id="b-project"
                className="df-input"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
              >
                <option value="">{t('bulk.noProject')}</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.slug}>
                    {p.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t('bulk.campaignName')} htmlFor="b-name">
              <TextInput
                id="b-name"
                value={campaignName}
                onChange={(e) => setCampaignName(e.target.value)}
              />
            </Field>
          </div>

          {mode === 'contacts' ? (
            <div className="bulk-contacts-mode">
              <Field label={t('bulk.template')} htmlFor="b-template">
                <textarea
                  id="b-template"
                  className="df-input"
                  rows={3}
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                />
              </Field>
              <p className="muted-text">{t('bulk.templateHint')}</p>
              <Field label={t('bulk.searchContacts')} htmlFor="b-cq">
                <TextInput
                  id="b-cq"
                  value={contactQuery}
                  onChange={(e) => setContactQuery(e.target.value)}
                  placeholder={t('contacts.searchPlaceholder')}
                />
              </Field>
              <div className="toolbar" style={{ marginBottom: 8 }}>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setSelectedIds(filteredContacts.map((c) => c.id))}
                >
                  {t('bulk.selectVisible')}
                </Button>
                <Button type="button" variant="ghost" onClick={() => setSelectedIds([])}>
                  {t('bulk.clearSelection')}
                </Button>
                <span className="muted-text">
                  {t('bulk.selectedCount', { count: selectedIds.length })}
                </span>
              </div>
              <div className="checkbox-list bulk-contact-list">
                {filteredContacts.map((c) => (
                  <label key={c.id} className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(c.id)}
                      onChange={(e) => toggleContact(c.id, e.target.checked)}
                    />
                    <span>
                      <strong>{c.name || t('contacts.unnamed')}</strong>
                      <span className="muted-text"> · {c.phone_number}</span>
                      {c.source_device_name ? (
                        <span className="contacts-device-chip"> {c.source_device_name}</span>
                      ) : null}
                    </span>
                  </label>
                ))}
                {!filteredContacts.length ? (
                  <p className="muted-text">{t('bulk.noContacts')}</p>
                ) : null}
              </div>
            </div>
          ) : (
            <Field label={t('bulk.csv')} htmlFor="b-csv">
              <textarea
                id="b-csv"
                className="df-input"
                rows={6}
                value={csv}
                onChange={(e) => setCsv(e.target.value)}
                style={{ fontFamily: 'ui-monospace, monospace', fontSize: 13 }}
              />
            </Field>
          )}

          <div className="toolbar">
            <Button type="submit" disabled={busy}>
              {t('bulk.start')}
            </Button>
            <Button type="button" variant="secondary" onClick={() => void onExport()}>
              {t('bulk.export')}
            </Button>
          </div>
        </form>
      </section>

      <div className="table-wrap" style={{ marginBottom: 24 }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('bulk.name')}</th>
              <th>{t('bulk.status')}</th>
              <th>{t('bulk.progress')}</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>
                  <span className={`status-chip status-${c.status}`}>{c.status}</span>
                </td>
                <td>
                  {c.sent}/{c.total} ({c.failed} {t('bulk.failed')})
                </td>
              </tr>
            ))}
            {!campaigns.length ? (
              <tr>
                <td colSpan={3}>{t('bulk.empty')}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {exports.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('bulk.exportId')}</th>
                <th>{t('bulk.status')}</th>
                <th>{t('bulk.rows')}</th>
              </tr>
            </thead>
            <tbody>
              {exports.map((e) => (
                <tr key={e.id}>
                  <td>
                    <code>{e.id.slice(0, 8)}…</code>
                  </td>
                  <td>{e.status}</td>
                  <td>{e.row_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}
