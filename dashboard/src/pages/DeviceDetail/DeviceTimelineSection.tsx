import { useTranslation } from 'react-i18next'
import type { DeviceEvent, EventsPagination } from '../../shared/api/ops'
import { Button } from '../../shared/ui/Form'

type Tone = 'info' | 'success' | 'warning' | 'danger' | 'neutral'

function asString(value: unknown): string | null {
  if (typeof value === 'string' && value.trim()) return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return null
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function formatWhen(iso: string, locale: string): { date: string; time: string; full: string } {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) {
    return { date: iso, time: '', full: iso }
  }
  return {
    date: d.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' }),
    time: d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    full: d.toLocaleString(locale),
  }
}

function eventTone(type: string): Tone {
  if (type.includes('failed') || type.includes('offline') || type.includes('revoked') || type.includes('dead')) {
    return 'danger'
  }
  if (type.includes('failover') || type.includes('retry')) {
    return 'warning'
  }
  if (
    type.includes('online') ||
    type.includes('paired') ||
    type.includes('acked') ||
    type.includes('sent') ||
    type.includes('delivered') ||
    type.includes('inbound')
  ) {
    return 'success'
  }
  if (type.startsWith('command.') || type.startsWith('pairing.')) {
    return 'info'
  }
  return 'neutral'
}

type Detail = { label: string; value: string }

function buildDetails(
  event: DeviceEvent,
  t: (key: string, opts?: Record<string, unknown>) => string,
): Detail[] {
  const p = event.payload || {}
  const details: Detail[] = []

  const push = (labelKey: string, value: unknown, fallbackLabel?: string) => {
    const text = asString(value)
    if (!text) return
    details.push({
      label: t(labelKey, { defaultValue: fallbackLabel || labelKey }),
      value: text,
    })
  }

  switch (event.type) {
    case 'pairing.created':
      push('detail.timelineFields.expiresAt', p.expires_at)
      break
    case 'device.paired':
      push('detail.timelineFields.agentVersion', p.agent_version)
      break
    case 'command.created':
    case 'command.acked': {
      push('detail.timelineFields.action', p.action)
      push('detail.timelineFields.status', p.status)
      push('detail.timelineFields.commandId', p.command_id)
      const result = asRecord(p.result)
      push('detail.timelineFields.ussdResponse', result.ussd_response)
      push('detail.timelineFields.ussdCode', result.ussd_code)
      push('detail.timelineFields.simSlot', result.sim_slot)
      if (typeof result.awaiting_input === 'boolean') {
        push(
          'detail.timelineFields.awaitingInput',
          result.awaiting_input ? t('common.yes', { defaultValue: 'yes' }) : t('common.no', { defaultValue: 'no' }),
        )
      }
      break
    }
    case 'permission.revoked':
      push(
        'detail.timelineFields.permission',
        t(`detail.permission.${String(p.permission)}`, {
          defaultValue: String(p.permission || ''),
        }),
      )
      break
    case 'sms.failover':
      push('detail.timelineFields.messageId', p.message_id)
      push('detail.timelineFields.fromDevice', p.from_device)
      break
    case 'sms.inbound':
      push('detail.timelineFields.from', p.from || p.sender)
      push('detail.timelineFields.body', p.body || p.text)
      push('detail.timelineFields.messageId', p.message_id)
      break
    default:
      if (event.type.startsWith('sms.')) {
        push('detail.timelineFields.to', p.to || p.to_number)
        push('detail.timelineFields.messageId', p.message_id)
        push('detail.timelineFields.status', p.status)
      } else {
        for (const [key, value] of Object.entries(p)) {
          if (value == null || typeof value === 'object') continue
          push(`detail.timelineFields.${key}`, value, key.replace(/_/g, ' '))
        }
      }
  }

  return details
}

type Props = {
  events: DeviceEvent[]
  pagination: EventsPagination | null
  onPageChange: (page: number) => void
  loading?: boolean
}

export function DeviceTimelineSection({
  events,
  pagination,
  onPageChange,
  loading,
}: Props) {
  const { t, i18n } = useTranslation()

  return (
    <section className="panel device-timeline">
      <div className="device-timeline-header">
        <h2 style={{ fontSize: 16, margin: 0 }}>{t('detail.timeline')}</h2>
        {pagination ? (
          <span className="muted-text">
            {t('detail.timelinePage', {
              page: pagination.page,
              total: pagination.total_pages,
              count: pagination.total,
            })}
          </span>
        ) : null}
      </div>

      {!events.length ? (
        <p className="muted-text">{loading ? t('common.loading') : t('detail.noEvents')}</p>
      ) : (
        <ol className="event-timeline">
          {events.map((event) => {
            const tone = eventTone(event.type)
            const when = formatWhen(event.created_at, i18n.language)
            const title = t(`detail.eventType.${event.type}`, {
              defaultValue: event.type.replace(/\./g, ' · '),
            })
            const details = buildDetails(event, t)

            return (
              <li key={event.id} className={`event-item event-tone-${tone}`}>
                <div className="event-rail" aria-hidden>
                  <span className="event-dot" />
                </div>
                <article className="event-card">
                  <header className="event-card-head">
                    <div className="event-title-row">
                      <span className={`event-type-chip event-chip-${tone}`}>{title}</span>
                    </div>
                    <time className="event-when" dateTime={event.created_at} title={when.full}>
                      <span className="event-date">{when.date}</span>
                      <span className="event-time">{when.time}</span>
                    </time>
                  </header>
                  {details.length > 0 ? (
                    <dl className="event-details">
                      {details.map((d) => (
                        <div key={`${event.id}-${d.label}`} className="event-detail">
                          <dt>{d.label}</dt>
                          <dd>{d.value}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : (
                    <p className="event-empty-detail muted-text">
                      {t('detail.timelineNoDetails')}
                    </p>
                  )}
                </article>
              </li>
            )
          })}
        </ol>
      )}

      {pagination && pagination.total_pages > 1 ? (
        <div className="timeline-pager">
          <Button
            type="button"
            variant="secondary"
            disabled={!pagination.has_prev || loading}
            onClick={() => onPageChange(pagination.page - 1)}
          >
            {t('detail.prevPage')}
          </Button>
          <span className="muted-text">
            {pagination.page} / {pagination.total_pages}
          </span>
          <Button
            type="button"
            variant="secondary"
            disabled={!pagination.has_next || loading}
            onClick={() => onPageChange(pagination.page + 1)}
          >
            {t('detail.nextPage')}
          </Button>
        </div>
      ) : null}
    </section>
  )
}
