import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { listDevices, type Device } from '../../shared/api/devices'
import {
  createProject,
  createProjectRoute,
  deleteProjectRoute,
  listProjectRoutes,
  listProjects,
  setProjectDevices,
  type Project,
  type ProjectDeviceSettings,
  type ProjectRouteBinding,
} from '../../shared/api/projects'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { useAuthStore } from '../../features/auth/authStore'
import { displayDeviceStatus } from '../../shared/lib/deviceStatus'

type DraftSettings = Record<string, ProjectDeviceSettings>

const defaultDeviceSettings = (): ProjectDeviceSettings => ({
  preferred_sim_slot: null,
  sim_fallback_enabled: true,
})

function deviceLabel(device: Pick<Device, 'name' | 'status' | 'last_seen_at' | 'agent_version'>) {
  const status = displayDeviceStatus(device)
  const ver = device.agent_version ? ` · v${device.agent_version}` : ''
  return `${device.name} (${status}${ver})`
}

function simOptionLabel(
  device: Device,
  slotIndex: number,
  t: (key: string, opts?: Record<string, unknown>) => string,
) {
  const sim = device.sims.find((s) => s.slot_index === slotIndex)
  if (!sim) return t('projects.simSlot', { slot: slotIndex })
  const operator = sim.operator ? ` · ${sim.operator}` : ''
  const number = sim.phone_number ? ` · ${sim.phone_number}` : ''
  return t('projects.simSlot', { slot: slotIndex }) + operator + number
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
  const [draftDeviceSettings, setDraftDeviceSettings] = useState<DraftSettings>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [routesByProject, setRoutesByProject] = useState<
    Record<string, ProjectRouteBinding[]>
  >({})
  const [routeDrafts, setRouteDrafts] = useState<
    Record<string, { route_key: string; label: string; device_id: string }>
  >({})

  const pairedDevices = useMemo(
    () => devices.filter((d) => d.is_paired),
    [devices],
  )

  const devicesById = useMemo(() => {
    const map = new Map<string, Device>()
    for (const d of pairedDevices) map.set(d.id, d)
    return map
  }, [pairedDevices])

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
    const routeEntries = await Promise.all(
      p.results.map(async (project) => {
        try {
          const res = await listProjectRoutes(token, project.id)
          return [project.id, res.results] as const
        } catch {
          return [project.id, [] as ProjectRouteBinding[]] as const
        }
      }),
    )
    setRoutesByProject(Object.fromEntries(routeEntries))
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
    const settings: DraftSettings = {}
    for (const d of project.devices || []) {
      settings[d.device_id] = {
        preferred_sim_slot: d.preferred_sim_slot ?? null,
        sim_fallback_enabled: d.sim_fallback_enabled ?? true,
        priority: d.priority,
      }
    }
    setEditingId(project.id)
    setDraftDeviceIds((project.devices || []).map((d) => d.device_id))
    setDraftDeviceSettings(settings)
    setNotice(null)
    setError(null)
  }

  function cancelEdit() {
    setEditingId(null)
    setDraftDeviceIds([])
    setDraftDeviceSettings({})
  }

  async function saveDevices(projectId: string) {
    if (!token) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const deviceSettings: DraftSettings = {}
      for (const id of draftDeviceIds) {
        deviceSettings[id] = draftDeviceSettings[id] ?? defaultDeviceSettings()
      }
      await setProjectDevices(token, projectId, draftDeviceIds, deviceSettings)
      setNotice(t('projects.devicesSaved'))
      setEditingId(null)
      setDraftDeviceIds([])
      setDraftDeviceSettings({})
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
    if (checked) {
      setDraftDeviceSettings((prev) => ({
        ...prev,
        [deviceId]: prev[deviceId] ?? defaultDeviceSettings(),
      }))
    }
  }

  function updateDraftSetting(
    deviceId: string,
    patch: Partial<ProjectDeviceSettings>,
  ) {
    setDraftDeviceSettings((prev) => ({
      ...prev,
      [deviceId]: { ...(prev[deviceId] ?? defaultDeviceSettings()), ...patch },
    }))
  }

  function routeDraft(projectId: string) {
    return (
      routeDrafts[projectId] ?? {
        route_key: '',
        label: '',
        device_id: '',
      }
    )
  }

  function updateRouteDraft(
    projectId: string,
    patch: Partial<{ route_key: string; label: string; device_id: string }>,
  ) {
    setRouteDrafts((prev) => ({
      ...prev,
      [projectId]: { ...routeDraft(projectId), ...patch },
    }))
  }

  async function addRoute(project: Project) {
    if (!token) return
    const draft = routeDraft(project.id)
    const deviceId = draft.device_id || (project.devices || [])[0]?.device_id || ''
    if (!draft.route_key.trim() || !deviceId) {
      setError(t('common.error'))
      return
    }
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await createProjectRoute(token, project.id, {
        route_key: draft.route_key.trim(),
        device_id: deviceId,
        label: draft.label.trim(),
      })
      setRouteDrafts((prev) => ({
        ...prev,
        [project.id]: { route_key: '', label: '', device_id: '' },
      }))
      setNotice(t('projects.routeAdded'))
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  async function removeRoute(projectId: string, routeId: string) {
    if (!token) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await deleteProjectRoute(token, projectId, routeId)
      setNotice(t('projects.routeDeleted'))
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  function formatPreferredSim(deviceId: string, slot: number | null) {
    if (slot == null) return t('projects.simAuto')
    const device = devicesById.get(deviceId)
    if (!device) return t('projects.simSlot', { slot })
    return simOptionLabel(device, slot, t)
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
                              <span className="project-sim-pref muted-text">
                                {t('projects.preferredSim')}:{' '}
                                {formatPreferredSim(d.device_id, d.preferred_sim_slot ?? null)}
                                {!d.sim_fallback_enabled
                                  ? ` · ${t('projects.simFallbackOff')}`
                                  : ''}
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
                    <p className="muted-text">{t('projects.simHint')}</p>
                    {!pairedDevices.length ? (
                      <p>{t('projects.noPairedDevices')}</p>
                    ) : (
                      <div className="project-edit-device-grid">
                        {pairedDevices.map((d) => {
                          const checked = draftDeviceIds.includes(d.id)
                          const settings = draftDeviceSettings[d.id] ?? defaultDeviceSettings()
                          const activeSlots = d.sims.filter((s) => s.is_active)
                          return (
                            <div
                              key={d.id}
                              className={`project-edit-device-card ${checked ? 'is-selected' : ''}`}
                            >
                              <label className="checkbox-row project-check-row">
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

                              {checked ? (
                                <div className="project-sim-settings">
                                  <Field
                                    label={t('projects.preferredSim')}
                                    htmlFor={`sim-${project.id}-${d.id}`}
                                  >
                                    <select
                                      id={`sim-${project.id}-${d.id}`}
                                      className="df-input"
                                      value={
                                        settings.preferred_sim_slot == null
                                          ? ''
                                          : String(settings.preferred_sim_slot)
                                      }
                                      onChange={(e) =>
                                        updateDraftSetting(d.id, {
                                          preferred_sim_slot: e.target.value
                                            ? Number(e.target.value)
                                            : null,
                                        })
                                      }
                                    >
                                      <option value="">{t('projects.simAuto')}</option>
                                      {activeSlots.map((sim) => (
                                        <option key={sim.id} value={sim.slot_index}>
                                          {simOptionLabel(d, sim.slot_index, t)}
                                        </option>
                                      ))}
                                    </select>
                                  </Field>
                                  <label className="checkbox-row project-fallback-row">
                                    <input
                                      type="checkbox"
                                      checked={settings.sim_fallback_enabled ?? true}
                                      onChange={(e) =>
                                        updateDraftSetting(d.id, {
                                          sim_fallback_enabled: e.target.checked,
                                        })
                                      }
                                    />
                                    <span>{t('projects.simFallback')}</span>
                                  </label>
                                </div>
                              ) : null}
                            </div>
                          )
                        })}
                      </div>
                    )}
                    <p className="muted-text project-draft-count">
                      {t('projects.selectedCount', { count: draftDeviceIds.length })}
                    </p>
                  </div>
                )}

                {!editing && count > 0 ? (
                  <div className="project-routes">
                    <h3 className="project-section-title">{t('projects.routesTitle')}</h3>
                    <p className="muted-text">{t('projects.routesHint')}</p>
                    {(routesByProject[project.id] || []).length === 0 ? (
                      <p className="muted-text">{t('projects.routesEmpty')}</p>
                    ) : (
                      <ul className="project-device-list">
                        {(routesByProject[project.id] || []).map((route) => (
                          <li key={route.id} className="project-device-row">
                            <div className="project-device-main">
                              <strong>
                                <code>{route.route_key}</code>
                                {route.label ? ` · ${route.label}` : ''}
                              </strong>
                              <span className="muted-text">
                                {route.device_name}
                                {route.preferred_sim_slot
                                  ? ` · ${t('projects.simSlot', { slot: route.preferred_sim_slot })}`
                                  : ''}
                                {!route.is_active ? ` · ${t('projects.routeInactive')}` : ''}
                              </span>
                            </div>
                            <Button
                              type="button"
                              variant="ghost"
                              disabled={busy}
                              onClick={() => void removeRoute(project.id, route.id)}
                            >
                              {t('projects.routeDelete')}
                            </Button>
                          </li>
                        ))}
                      </ul>
                    )}
                    <div className="toolbar project-create-grid" style={{ marginTop: 12 }}>
                      <Field label={t('projects.routeKey')} htmlFor={`rk-${project.id}`}>
                        <TextInput
                          id={`rk-${project.id}`}
                          value={routeDraft(project.id).route_key}
                          onChange={(e) =>
                            updateRouteDraft(project.id, { route_key: e.target.value })
                          }
                          placeholder="customer-uuid"
                        />
                      </Field>
                      <Field label={t('projects.routeLabel')} htmlFor={`rl-${project.id}`}>
                        <TextInput
                          id={`rl-${project.id}`}
                          value={routeDraft(project.id).label}
                          onChange={(e) =>
                            updateRouteDraft(project.id, { label: e.target.value })
                          }
                        />
                      </Field>
                      <Field label={t('projects.routeDevice')} htmlFor={`rd-${project.id}`}>
                        <select
                          id={`rd-${project.id}`}
                          className="df-input"
                          value={
                            routeDraft(project.id).device_id || linked[0]?.device_id || ''
                          }
                          onChange={(e) =>
                            updateRouteDraft(project.id, { device_id: e.target.value })
                          }
                        >
                          {linked.map((d) => (
                            <option key={d.device_id} value={d.device_id}>
                              {d.name}
                            </option>
                          ))}
                        </select>
                      </Field>
                      <Button
                        type="button"
                        disabled={busy}
                        onClick={() => void addRoute(project)}
                      >
                        {t('projects.routeAdd')}
                      </Button>
                    </div>
                  </div>
                ) : null}
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
