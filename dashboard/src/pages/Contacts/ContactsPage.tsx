import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { listDevices, type Device } from '../../shared/api/devices'
import { fetchDeviceCommand, sendDeviceCommand } from '../../shared/api/ops'
import {
  confirmContactImport,
  createContact,
  listContacts,
  previewContactImport,
  updateContact,
  type Contact,
  type ContactImportPreview,
  type ContactImportPreviewRow,
} from '../../shared/api/phase6'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { Modal } from '../../shared/ui/Modal'
import { useAuthStore } from '../../features/auth/authStore'
import { displayDeviceStatus } from '../../shared/lib/deviceStatus'

type PreviewItem = ContactImportPreviewRow & { key: string; selected: boolean }

function rowKey(row: ContactImportPreviewRow, prefix: string, index: number) {
  return `${prefix}:${row.phone || row.phone_raw || ''}:${index}`
}

async function waitForCommand(
  token: string,
  deviceId: string,
  commandId: string,
  signal: AbortSignal,
) {
  const started = Date.now()
  while (!signal.aborted && Date.now() - started < 90_000) {
    const cmd = await fetchDeviceCommand(token, deviceId, commandId)
    if (cmd.status === 'acked' || cmd.status === 'failed') return cmd
    await new Promise((r) => setTimeout(r, 1000))
  }
  throw new Error('timeout')
}

export function ContactsPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [items, setItems] = useState<Contact[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [phone, setPhone] = useState('')
  const [name, setName] = useState('')
  const [search, setSearch] = useState('')
  const [deviceFilter, setDeviceFilter] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [importOpen, setImportOpen] = useState(false)
  const [importDeviceId, setImportDeviceId] = useState('')
  const [importPhase, setImportPhase] = useState<
    'pick' | 'fetching' | 'validating' | 'preview' | 'importing'
  >('pick')
  const [preview, setPreview] = useState<ContactImportPreview | null>(null)
  const [previewItems, setPreviewItems] = useState<PreviewItem[]>([])
  const [progress, setProgress] = useState({ done: 0, total: 0, label: '' })
  const abortRef = useRef<AbortController | null>(null)

  const pairedDevices = useMemo(
    () => devices.filter((d) => d.is_paired),
    [devices],
  )

  const sourceDevices = useMemo(() => {
    const map = new Map<string, string>()
    for (const c of items) {
      if (c.source_device) {
        map.set(c.source_device, c.source_device_name || c.source_device.slice(0, 8))
      }
    }
    for (const d of pairedDevices) {
      if (!map.has(d.id)) map.set(d.id, d.name)
    }
    return Array.from(map.entries()).map(([id, label]) => ({ id, label }))
  }, [items, pairedDevices])

  const refresh = useCallback(async () => {
    if (!token) return
    const [contacts, devs] = await Promise.all([
      listContacts(token, {
        q: search.trim() || undefined,
        device: deviceFilter || undefined,
      }),
      listDevices(token),
    ])
    setItems(contacts.results)
    setDevices(devs.results)
  }, [token, search, deviceFilter])

  useEffect(() => {
    const id = window.setTimeout(() => {
      void refresh().catch((err) => {
        setError(err instanceof ApiError ? err.message : t('common.error'))
      })
    }, search ? 250 : 0)
    return () => window.clearTimeout(id)
  }, [refresh, search, t])

  async function onCreate(event: FormEvent) {
    event.preventDefault()
    if (!token) return
    setBusy(true)
    setError(null)
    try {
      await createContact(token, { phone_number: phone, name })
      setPhone('')
      setName('')
      setNotice(t('contacts.created'))
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  function openImport() {
    setImportOpen(true)
    setImportPhase('pick')
    setPreview(null)
    setPreviewItems([])
    setError(null)
    if (!importDeviceId && pairedDevices[0]) {
      setImportDeviceId(pairedDevices[0].id)
    }
  }

  function closeImport() {
    abortRef.current?.abort()
    abortRef.current = null
    setImportOpen(false)
    setImportPhase('pick')
    setPreview(null)
    setPreviewItems([])
    setProgress({ done: 0, total: 0, label: '' })
  }

  function applyPreview(data: ContactImportPreview) {
    setPreview(data)
    const rows: PreviewItem[] = [
      ...data.valid.map((row, i) => ({
        ...row,
        key: rowKey(row, 'v', i),
        selected: true,
      })),
      ...data.invalid.map((row, i) => ({
        ...row,
        key: rowKey(row, 'i', i),
        selected: false,
      })),
    ]
    setPreviewItems(rows)
    setImportPhase('preview')
  }

  async function fetchFromDevice() {
    if (!token || !importDeviceId) return
    setBusy(true)
    setError(null)
    setImportPhase('fetching')
    setProgress({ done: 0, total: 0, label: t('contacts.progressWaitingDevice') })
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac
    try {
      const cmd = await sendDeviceCommand(token, importDeviceId, 'contacts_read', {
        limit: 3000,
      })
      const done = await waitForCommand(token, importDeviceId, cmd.id, ac.signal)
      if (done.status === 'failed') {
        const code = String(done.result?.error_code || done.result?.error || 'failed')
        throw new Error(t('contacts.fetchFailed', { code }))
      }
      const raw = done.result?.contacts
      const contacts = Array.isArray(raw)
        ? (raw as Array<Record<string, unknown>>).map((row) => ({
            name: String(row.name || ''),
            phone: String(row.phone || row.phone_number || row.number || ''),
          }))
        : []
      if (!contacts.length) {
        setError(t('contacts.fetchEmpty'))
        setImportPhase('pick')
        setProgress({ done: 0, total: 0, label: '' })
        return
      }
      setImportPhase('validating')
      setProgress({
        done: 0,
        total: contacts.length,
        label: t('contacts.progressValidating', { count: contacts.length }),
      })
      const data = await previewContactImport(token, {
        device_id: importDeviceId,
        contacts,
      })
      applyPreview(data)
      setProgress({ done: 0, total: 0, label: '' })
    } catch (err) {
      if (ac.signal.aborted) return
      setImportPhase('pick')
      setProgress({ done: 0, total: 0, label: '' })
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : t('common.error'),
      )
    } finally {
      setBusy(false)
    }
  }

  async function confirmImport() {
    if (!token) return
    const selected = previewItems.filter((r) => r.selected && !r.reason)
    if (!selected.length) {
      setError(t('contacts.noneSelected'))
      return
    }
    setBusy(true)
    setError(null)
    setImportPhase('importing')
    const chunkSize = 75
    let created = 0
    let updated = 0
    let rejected = 0
    try {
      for (let i = 0; i < selected.length; i += chunkSize) {
        const chunk = selected.slice(i, i + chunkSize)
        setProgress({
          done: i,
          total: selected.length,
          label: t('contacts.progressImporting', {
            done: Math.min(i + chunk.length, selected.length),
            total: selected.length,
          }),
        })
        const result = await confirmContactImport(token, {
          device_id: importDeviceId || undefined,
          contacts: chunk.map((r) => ({ name: r.name, phone: r.phone })),
          update_existing: true,
        })
        created += result.created
        updated += result.updated
        rejected += result.rejected
      }
      setProgress({
        done: selected.length,
        total: selected.length,
        label: t('contacts.progressDone'),
      })
      setNotice(
        t('contacts.importDone', {
          created,
          updated,
          rejected,
        }),
      )
      closeImport()
      await refresh()
    } catch (err) {
      setImportPhase('preview')
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  const selectedCount = previewItems.filter((r) => r.selected && !r.reason).length
  const invalidCount = previewItems.filter((r) => r.reason).length

  return (
    <div>
      <header className="page-header">
        <h1>{t('contacts.title')}</h1>
        <p>{t('contacts.subtitle')}</p>
      </header>

      {error ? <div className="auth-error">{error}</div> : null}
      {notice ? <div className="auth-success">{notice}</div> : null}

      <section className="panel contacts-toolbar-panel">
        <div className="contacts-toolbar">
          <Field label={t('contacts.search')} htmlFor="c-search">
            <TextInput
              id="c-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('contacts.searchPlaceholder')}
            />
          </Field>
          <Field label={t('contacts.filterDevice')} htmlFor="c-device-filter">
            <select
              id="c-device-filter"
              className="df-input"
              value={deviceFilter}
              onChange={(e) => setDeviceFilter(e.target.value)}
            >
              <option value="">{t('contacts.allDevices')}</option>
              {sourceDevices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.label}
                </option>
              ))}
            </select>
          </Field>
          <Button type="button" variant="secondary" onClick={openImport}>
            {t('contacts.importFromDevice')}
          </Button>
        </div>
      </section>

      <section className="panel" style={{ marginBottom: 24 }}>
        <h2 className="contacts-section-title">{t('contacts.create')}</h2>
        <form className="auth-form" onSubmit={(e) => void onCreate(e)}>
          <div className="toolbar">
            <Field label={t('contacts.phone')} htmlFor="c-phone">
              <TextInput
                id="c-phone"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+98912… / 09…"
                required
              />
            </Field>
            <Field label={t('contacts.name')} htmlFor="c-name">
              <TextInput id="c-name" value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Button type="submit" disabled={busy}>
              {t('contacts.create')}
            </Button>
          </div>
        </form>
      </section>

      <div className="contacts-meta muted-text">
        {t('contacts.count', { count: items.length })}
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('contacts.name')}</th>
              <th>{t('contacts.phone')}</th>
              <th>{t('contacts.sourceDevice')}</th>
              <th>{t('contacts.lists')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td>{c.name || t('contacts.unnamed')}</td>
                <td>
                  <code>{c.phone_number}</code>
                </td>
                <td>
                  {c.source_device_name ? (
                    <span className="contacts-device-chip">{c.source_device_name}</span>
                  ) : (
                    <span className="muted-text">{t('contacts.manual')}</span>
                  )}
                </td>
                <td>
                  {c.is_blacklisted ? (
                    <span className="status-chip status-failed">{t('contacts.blacklisted')}</span>
                  ) : null}
                  {c.is_whitelisted ? (
                    <span className="status-chip status-online">{t('contacts.whitelisted')}</span>
                  ) : null}
                </td>
                <td>
                  <button
                    type="button"
                    className="df-btn df-btn-ghost"
                    onClick={() =>
                      void updateContact(token!, c.id, {
                        is_blacklisted: !c.is_blacklisted,
                      }).then(() => refresh())
                    }
                  >
                    {c.is_blacklisted ? t('contacts.unblacklist') : t('contacts.blacklist')}
                  </button>
                </td>
              </tr>
            ))}
            {!items.length ? (
              <tr>
                <td colSpan={5}>{t('contacts.empty')}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <Modal
        open={importOpen}
        onClose={closeImport}
        title={t('contacts.importTitle')}
        wide
        footer={
          importPhase === 'preview' ? (
            <div className="toolbar">
              <Button type="button" variant="ghost" onClick={closeImport} disabled={busy}>
                {t('contacts.cancel')}
              </Button>
              <Button type="button" onClick={() => void confirmImport()} disabled={busy || !selectedCount}>
                {t('contacts.importSelected', { count: selectedCount })}
              </Button>
            </div>
          ) : importPhase === 'importing' || importPhase === 'fetching' || importPhase === 'validating' ? (
            <Button type="button" variant="ghost" onClick={closeImport} disabled={importPhase === 'importing'}>
              {t('contacts.cancel')}
            </Button>
          ) : null
        }
      >
        {['fetching', 'validating', 'importing'].includes(importPhase) ? (
          <div className="contacts-import-progress">
            <p>{progress.label || t('contacts.fetching')}</p>
            <div className="df-progress">
              <div
                className={`df-progress-bar ${progress.total ? '' : 'is-indeterminate'}`}
                style={
                  progress.total
                    ? { width: `${Math.min(100, Math.round((progress.done / progress.total) * 100))}%` }
                    : undefined
                }
              />
            </div>
            {progress.total ? (
              <p className="muted-text">
                {progress.done}/{progress.total}
              </p>
            ) : (
              <p className="muted-text">{t('contacts.progressHint')}</p>
            )}
          </div>
        ) : null}

        {importPhase === 'pick' ? (
          <div className="contacts-import-pick">
            <p className="muted-text">{t('contacts.importHint')}</p>
            <Field label={t('contacts.importDevice')} htmlFor="import-device">
              <select
                id="import-device"
                className="df-input"
                value={importDeviceId}
                disabled={busy}
                onChange={(e) => setImportDeviceId(e.target.value)}
              >
                <option value="">{t('contacts.selectDevice')}</option>
                {pairedDevices.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({displayDeviceStatus(d)})
                  </option>
                ))}
              </select>
            </Field>
            <Button
              type="button"
              disabled={busy || !importDeviceId}
              onClick={() => void fetchFromDevice()}
            >
              {t('contacts.fetchContacts')}
            </Button>
          </div>
        ) : null}

        {importPhase === 'preview' && preview ? (
          <div className="contacts-import-preview">
            <div className="contacts-import-summary">
              <span>{t('contacts.previewValid', { count: preview.summary.valid })}</span>
              <span>{t('contacts.previewInvalid', { count: preview.summary.invalid })}</span>
              <span>
                {t('contacts.previewExisting', { count: preview.summary.already_exist })}
              </span>
            </div>
            <p className="muted-text">{t('contacts.previewHint')}</p>
            <div className="toolbar" style={{ marginBottom: 8 }}>
              <Button
                type="button"
                variant="secondary"
                onClick={() =>
                  setPreviewItems((prev) =>
                    prev.map((r) => ({ ...r, selected: !r.reason })),
                  )
                }
              >
                {t('contacts.selectAllValid')}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() =>
                  setPreviewItems((prev) => prev.map((r) => ({ ...r, selected: false })))
                }
              >
                {t('contacts.selectNone')}
              </Button>
            </div>
            <div className="contacts-preview-list">
              {previewItems.map((row) => {
                const invalid = Boolean(row.reason)
                return (
                  <label
                    key={row.key}
                    className={`contacts-preview-row ${invalid ? 'is-invalid' : ''} ${row.exists ? 'is-existing' : ''}`}
                  >
                    <input
                      type="checkbox"
                      disabled={invalid}
                      checked={row.selected && !invalid}
                      onChange={(e) =>
                        setPreviewItems((prev) =>
                          prev.map((r) =>
                            r.key === row.key ? { ...r, selected: e.target.checked } : r,
                          ),
                        )
                      }
                    />
                    <div className="contacts-preview-main">
                      <strong>{row.name || t('contacts.unnamed')}</strong>
                      <span>
                        <code>{row.phone || row.phone_raw || '—'}</code>
                        {row.phone_raw && row.phone && row.phone_raw !== row.phone
                          ? ` ← ${row.phone_raw}`
                          : null}
                      </span>
                    </div>
                    <span className="contacts-preview-badge">
                      {invalid
                        ? t(`contacts.reason.${row.reason}`, {
                            defaultValue: row.reason || 'invalid',
                          })
                        : row.exists
                          ? t('contacts.willUpdate')
                          : t('contacts.willCreate')}
                    </span>
                  </label>
                )
              })}
            </div>
            {invalidCount ? (
              <p className="muted-text">{t('contacts.invalidSkipped', { count: invalidCount })}</p>
            ) : null}
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
