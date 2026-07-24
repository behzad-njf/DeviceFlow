import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { listDevices, type Device } from '../../shared/api/devices'
import {
  createProject,
  listProjects,
  setProjectDevices,
  type Project,
} from '../../shared/api/projects'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'
import { displayDeviceStatus } from '../../shared/lib/deviceStatus'

function deviceLabel(device: Pick<Device, 'name' | 'status' | 'last_seen_at' | 'agent_version'>) {
  const status = displayDeviceStatus(device)
  const ver = device.agent_version ? ` · v${device.agent_version}` : ''
  return `${device.name} (${status}${ver})`
}

export function ProjectsPage() {
  const { t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [projects, setProjects] = useState<Project[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [mode, setMode] = useState('transactional')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draftDeviceIds, setDraftDeviceIds] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const pairedDevices = useMemo(
    () => devices.filter((d) => d.is_paired),
    [devices],
  )

  const attachedDeviceIds = useMemo(() => {
    const ids = new Set<string>()
    for (const p of projects) {
      for (const d of p.devices || []) ids.add(d.device_id)
    }
    return ids
  }, [projects])

  const unattachedDevices = useMemo(
    () => pairedDevices.filter((d) => !attachedDeviceIds.has(d.id)),
    [pairedDevices, attachedDeviceIds],
  )

  const refresh = useCallback(async () => {
    if (!token) return
    const [p, d] = await Promise.all([listProjects(token), listDevices(token)])
    setProjects(p.results)
    setDevices(d.results)
  }, [token])

  useEffect(() => {
    void refresh().catch((err) => {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    })
  }, [refresh, t])

  async function onCreate(event: FormEvent) {
    event.preventDefault()
    if (!token) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await createProject(token, { name, slug, mode_default: mode })
      setName('')
      setSlug('')
      setMode('transactional')
      setNotice(t('projects.created'))
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  function startEdit(project: Project) {
    setEditingId(project.id)
    setDraftDeviceIds((project.devices || []).map((d) => d.device_id))
    setNotice(null)
    setError(null)
  }

  function cancelEdit() {
    setEditingId(null)
    setDraftDeviceIds([])
  }

  async function saveDevices(projectId: string) {
    if (!token) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await setProjectDevices(token, projectId, draftDeviceIds)
      setNotice(t('projects.devicesSaved'))
      setEditingId(null)
      setDraftDeviceIds([])
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  function toggleDraft(deviceId: string, checked: boolean) {
    setDraftDeviceIds((prev) =>
      checked ? [...prev, deviceId] : prev.filter((id) => id !== deviceId),
    )
  }

  return (
    <div>
      <header className="page-header">
        <h1>{t('projects.title')}</h1>
        <p>{t('projects.subtitle')}</p>
      </header>

      {error ? <div className="auth-error">{error}</div> : null}
      {notice ? <div className="auth-success">{notice}</div> : null}

      <section className="panel project-create-panel">
        <h2 className="project-section-title">{t('projects.create')}</h2>
        <form className="auth-form" onSubmit={(e) => void onCreate(e)}>
          <div className="toolbar project-create-grid">
            <Field label={t('projects.name')} htmlFor="pname">
              <TextInput
                id="pname"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </Field>
            <Field label={t('projects.slug')} htmlFor="pslug">
              <TextInput
                id="pslug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                required
              />
            </Field>
            <Field label={t('projects.mode')} htmlFor="pmode">
              <select
                id="pmode"
                className="df-input"
                value={mode}
                onChange={(e) => setMode(e.target.value)}
              >
                <option value="transactional">{t('projects.modeTransactional')}</option>
                <option value="otp">{t('projects.modeOtp')}</option>
                <option value="marketing">{t('projects.modeMarketing')}</option>
              </select>
            </Field>
            <Button type="submit" disabled={busy}>
              {t('projects.create')}
            </Button>
          </div>
        </form>
      </section>

      {unattachedDevices.length > 0 ? (
        <section className="panel project-fleet-alert">
          <h2 className="project-section-title">{t('projects.unattachedTitle')}</h2>
          <p className="muted-text">{t('projects.unattachedHint')}</p>
          <div className="project-device-chips">
            {unattachedDevices.map((d) => (
              <span key={d.id} className="project-device-chip is-unattached">
                <span className={`status-dot status-${displayDeviceStatus(d)}`} />
                <Link to={`/devices/${d.id}`}>{d.name}</Link>
                <span className="muted-text">{displayDeviceStatus(d)}</span>
              </span>
            ))}
          </div>
        </section>
      ) : null}

      {!projects.length ? (
        <section className="panel">
          <p>{t('projects.empty')}</p>
        </section>
      ) : (
        <div className="project-card-list">
          {projects.map((project) => {
            const linked = project.devices || []
            const count = project.device_count ?? linked.length
            const editing = editingId === project.id

            return (
              <section key={project.id} className="panel project-card">
                <header className="project-card-head">
                  <div>
                    <div className="project-card-title-row">
                      <h2>{project.name}</h2>
                      <span
                        className={`project-badge ${project.is_active ? 'is-on' : 'is-off'}`}
                      >
                        {project.is_active ? t('projects.activeYes') : t('projects.activeNo')}
                      </span>
                    </div>
                    <p className="project-card-meta muted-text">
                      <code>{project.slug}</code>
                      <span aria-hidden>·</span>
                      {t('projects.mode')}: {project.mode_default}
                    </p>
                  </div>
                  <div className="project-card-actions">
                    <span
                      className={`project-attach-count ${count ? 'has-devices' : 'no-devices'}`}
                    >
                      {count
                        ? t('projects.attachedCount', { count })
                        : t('projects.attachedNone')}
                    </span>
                    {!editing ? (
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={busy}
                        onClick={() => startEdit(project)}
                      >
                        {t('projects.managePhones')}
                      </Button>
                    ) : (
                      <div className="toolbar">
                        <Button
                          type="button"
                          variant="ghost"
                          disabled={busy}
                          onClick={cancelEdit}
                        >
                          {t('projects.cancel')}
                        </Button>
                        <Button
                          type="button"
                          disabled={busy}
                          onClick={() => void saveDevices(project.id)}
                        >
                          {t('projects.saveDevices')}
                        </Button>
                      </div>
                    )}
                  </div>
                </header>

                {!editing ? (
                  count === 0 ? (
                    <div className="project-empty-devices">
                      <p>{t('projects.noPhonesBody')}</p>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => startEdit(project)}
                      >
                        {t('projects.attachPhones')}
                      </Button>
                    </div>
                  ) : (
                    <ul className="project-device-list">
                      {linked.map((d) => {
                        const shown = displayDeviceStatus({
                          status: d.status,
                          last_seen_at: d.last_seen_at,
                        })
                        return (
                          <li key={d.device_id} className="project-device-row">
                            <span className={`status-dot status-${shown}`} />
                            <div className="project-device-main">
                              <Link to={`/devices/${d.device_id}`}>{d.name}</Link>
                              <span className="muted-text">
                                {shown}
                                {d.agent_version ? ` · v${d.agent_version}` : ''}
                                {` · ${t('projects.health')} ${d.health_score}`}
                              </span>
                            </div>
                            <span className="project-priority muted-text">
                              {t('projects.priority')}: {d.priority}
                            </span>
                          </li>
                        )
                      })}
                    </ul>
                  )
                ) : (
                  <div className="project-edit-devices">
                    <p className="muted-text">{t('projects.manageHint')}</p>
                    {!pairedDevices.length ? (
                      <p>{t('projects.noPairedDevices')}</p>
                    ) : (
                      <div className="checkbox-list project-checkbox-list">
                        {pairedDevices.map((d) => {
                          const checked = draftDeviceIds.includes(d.id)
                          return (
                            <label key={d.id} className="checkbox-row project-check-row">
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(e) => toggleDraft(d.id, e.target.checked)}
                              />
                              <span className={`status-dot status-${displayDeviceStatus(d)}`} />
                              <span>{deviceLabel(d)}</span>
                              {attachedDeviceIds.has(d.id) &&
                              !(project.devices || []).some((x) => x.device_id === d.id) ? (
                                <span className="project-elsewhere muted-text">
                                  {t('projects.alsoElsewhere')}
                                </span>
                              ) : null}
                            </label>
                          )
                        })}
                      </div>
                    )}
                    <p className="muted-text project-draft-count">
                      {t('projects.selectedCount', { count: draftDeviceIds.length })}
                    </p>
                  </div>
                )}
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
