import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { fetchDeviceMap, type MapPoint } from '../../shared/api/analytics'
import { useAuthStore } from '../../features/auth/authStore'
import { dashboardSocket } from '../../shared/ws/client'
import { displayDeviceStatus } from '../../shared/lib/deviceStatus'

// Default marker icons break under Vite bundling — use div icons instead.
function statusIcon(status: string) {
  const color =
    status === 'online' ? '#2f9e44' : status === 'busy' ? '#f59f00' : '#868e96'
  return L.divIcon({
    className: 'df-map-marker',
    html: `<span class="df-map-pin" style="--pin:${color}"></span>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  })
}

function formatWhen(iso: string | null | undefined, locale: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(locale)
}

export function MapPage() {
  const { t, i18n } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const [points, setPoints] = useState<MapPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const mapEl = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layerRef = useRef<L.LayerGroup | null>(null)
  const fittedRef = useRef(false)

  const refresh = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchDeviceMap(token)
      setPoints(data.results)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('common.error'))
    } finally {
      setLoading(false)
    }
  }, [token, t])

  useEffect(() => {
    void refresh()
    const poll = window.setInterval(() => {
      void refresh().catch(() => undefined)
    }, 15_000)
    return () => window.clearInterval(poll)
  }, [refresh])

  // Near-realtime: patch pins when heartbeats publish device.updated with lat/lng.
  useEffect(() => {
    return dashboardSocket.onEvent((event) => {
      if (event.type !== 'device.updated') return
      const p = event.payload || {}
      const id = String(p.id || p.device_id || '')
      if (!id || p.lat == null || p.lng == null) return
      setPoints((prev) => {
        const next = [...prev]
        const idx = next.findIndex((x) => x.device_id === id)
        const patch: MapPoint = {
          device_id: id,
          name: String(p.name || next[idx]?.name || id),
          status: String(p.status || next[idx]?.status || 'online'),
          health_score: Number(p.health_score ?? next[idx]?.health_score ?? 0),
          lat: Number(p.lat),
          lng: Number(p.lng),
          city: String(p.city ?? next[idx]?.city ?? ''),
          accuracy_m:
            p.accuracy_m != null
              ? Number(p.accuracy_m)
              : next[idx]?.accuracy_m ?? null,
          last_seen_at:
            typeof p.last_seen_at === 'string'
              ? p.last_seen_at
              : next[idx]?.last_seen_at ?? null,
          location_received_at:
            typeof p.location_received_at === 'string'
              ? p.location_received_at
              : next[idx]?.location_received_at ?? '',
        }
        if (idx >= 0) next[idx] = { ...next[idx], ...patch }
        else next.push(patch)
        return next
      })
    })
  }, [])

  // Always mount the map container first, then init Leaflet (fixes empty grey/missing map).
  useEffect(() => {
    const el = mapEl.current
    if (!el || mapRef.current) return

    const map = L.map(el, {
      zoomControl: true,
      attributionControl: true,
    }).setView([32.0, 53.0], 5)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)

    layerRef.current = L.layerGroup().addTo(map)
    mapRef.current = map

    const onResize = () => map.invalidateSize()
    window.addEventListener('resize', onResize)
    window.setTimeout(onResize, 80)

    return () => {
      window.removeEventListener('resize', onResize)
      map.remove()
      mapRef.current = null
      layerRef.current = null
      fittedRef.current = false
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    const layer = layerRef.current
    if (!map || !layer) return

    layer.clearLayers()
    const latLngs: L.LatLngExpression[] = []

    for (const point of points) {
      const shown = displayDeviceStatus({
        status: point.status,
        last_seen_at: point.last_seen_at ?? null,
      })
      const marker = L.marker([Number(point.lat), Number(point.lng)], {
        icon: statusIcon(shown),
        title: point.name,
      })
      marker.bindPopup(
        `<strong>${point.name}</strong><br/>` +
          `${shown} · health ${point.health_score}` +
          (point.city ? `<br/>${point.city}` : '') +
          `<br/><a href="/devices/${point.device_id}">Open device</a>`,
      )
      marker.on('click', () => setSelectedId(point.device_id))
      marker.addTo(layer)
      latLngs.push([Number(point.lat), Number(point.lng)])
    }

    if (latLngs.length === 1) {
      map.setView(latLngs[0], 13)
      fittedRef.current = true
    } else if (latLngs.length > 1 && !fittedRef.current) {
      map.fitBounds(L.latLngBounds(latLngs).pad(0.35), { maxZoom: 14 })
      fittedRef.current = true
    }

    window.setTimeout(() => map.invalidateSize(), 50)
  }, [points])

  const selected = useMemo(
    () => points.find((p) => p.device_id === selectedId) || null,
    [points, selectedId],
  )

  return (
    <div>
      <header className="page-header">
        <h1>{t('map.title')}</h1>
        <p>{t('map.subtitle')}</p>
      </header>

      {error ? <div className="auth-error">{error}</div> : null}

      <section className="panel df-map-panel">
        <div className="df-map-stage">
          <div ref={mapEl} className="df-map-canvas" />
          {!loading && !points.length ? (
            <div className="df-map-empty-overlay">
              <p>{t('map.empty')}</p>
              <p className="muted-text">{t('map.hint')}</p>
            </div>
          ) : null}
        </div>

        {selected ? (
          <div className="df-map-sidecar">
            <h3>{selected.name}</h3>
            <p className="muted-text">
              {displayDeviceStatus({
                status: selected.status,
                last_seen_at: selected.last_seen_at ?? null,
              })}{' '}
              · {t('analytics.health')} {selected.health_score}
            </p>
            <dl className="df-map-meta">
              <div>
                <dt>{t('map.coords')}</dt>
                <dd>
                  {Number(selected.lat).toFixed(5)}, {Number(selected.lng).toFixed(5)}
                </dd>
              </div>
              {selected.accuracy_m != null ? (
                <div>
                  <dt>{t('map.accuracy')}</dt>
                  <dd>±{Math.round(Number(selected.accuracy_m))} m</dd>
                </div>
              ) : null}
              <div>
                <dt>{t('map.updated')}</dt>
                <dd>
                  {formatWhen(
                    selected.location_received_at || selected.last_seen_at,
                    i18n.language,
                  )}
                </dd>
              </div>
              {selected.city ? (
                <div>
                  <dt>{t('map.city')}</dt>
                  <dd>{selected.city}</dd>
                </div>
              ) : null}
            </dl>
            <Link className="df-btn df-btn-secondary" to={`/devices/${selected.device_id}`}>
              {t('map.openDevice')}
            </Link>
          </div>
        ) : (
          <p className="muted-text df-map-hint-inline">
            {points.length ? t('map.clickPin') : t('map.hint')}
          </p>
        )}
      </section>

      {points.length > 0 ? (
        <div className="table-wrap" style={{ marginTop: 16 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('devices.colName')}</th>
                <th>{t('map.city')}</th>
                <th>{t('map.coords')}</th>
                <th>{t('analytics.health')}</th>
                <th>{t('devices.colStatus')}</th>
                <th>{t('map.updated')}</th>
              </tr>
            </thead>
            <tbody>
              {points.map((p) => (
                <tr
                  key={p.device_id}
                  className={selectedId === p.device_id ? 'is-selected' : undefined}
                  onClick={() => {
                    setSelectedId(p.device_id)
                    mapRef.current?.setView([Number(p.lat), Number(p.lng)], 14)
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <td>
                    <Link to={`/devices/${p.device_id}`} onClick={(e) => e.stopPropagation()}>
                      {p.name}
                    </Link>
                  </td>
                  <td>{p.city || '—'}</td>
                  <td>
                    {Number(p.lat).toFixed(4)}, {Number(p.lng).toFixed(4)}
                  </td>
                  <td>{p.health_score}</td>
                  <td>
                    {displayDeviceStatus({
                      status: p.status,
                      last_seen_at: p.last_seen_at ?? null,
                    })}
                  </td>
                  <td>
                    {formatWhen(p.location_received_at || p.last_seen_at, i18n.language)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}
