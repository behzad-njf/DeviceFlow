import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { runDeviceAction } from '../../shared/api/ai'
import type { SimSlot } from '../../shared/api/devices'
import { fetchDeviceCommand, type DeviceCommand } from '../../shared/api/ops'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { Modal } from '../../shared/ui/Modal'

type Props = {
  open: boolean
  onClose: () => void
  token: string
  deviceId: string
  sims?: SimSlot[]
  onFinished?: () => void
}

type TranscriptEntry = {
  role: 'out' | 'in'
  text: string
  code?: string
}

/**
 * Many carriers (incl. IR) keep menu state as nested MMI:
 * *141# → reply 1 → *141*1# → reply 2 → *141*1*2#
 * Full codes (*…#) are sent as-is.
 */
export function composeUssdReply(previousCode: string, reply: string): string {
  const r = reply.trim()
  if (!r) return previousCode
  if (r.includes('*') || r.includes('#')) return r
  const root = previousCode.trim().replace(/#$/, '')
  if (!root.startsWith('*')) return r
  return `${root}*${r}#`
}

function simLabel(sim: SimSlot, t: (key: string, opts?: Record<string, unknown>) => string): string {
  const parts = [
    t('detail.simSlot', { slot: sim.slot_index }),
    sim.operator,
    sim.phone_number,
  ].filter(Boolean)
  return parts.join(' · ')
}

async function waitForCommand(
  token: string,
  deviceId: string,
  commandId: string,
  signal: AbortSignal,
): Promise<DeviceCommand> {
  const started = Date.now()
  // Dial + accessibility scrape can take ~30–40s on MIUI.
  while (!signal.aborted && Date.now() - started < 90_000) {
    const cmd = await fetchDeviceCommand(token, deviceId, commandId)
    if (cmd.status === 'acked' || cmd.status === 'failed') return cmd
    await new Promise((r) => setTimeout(r, 1000))
  }
  throw new Error('timeout')
}

export function UssdModal({ open, onClose, token, deviceId, sims = [], onFinished }: Props) {
  const { t } = useTranslation()
  const activeSims = useMemo(
    () => (sims.length ? sims.filter((s) => s.is_active !== false) : sims),
    [sims],
  )
  const multiSim = activeSims.length > 1

  const [code, setCode] = useState('*141#')
  const [reply, setReply] = useState('')
  const [simSlot, setSimSlot] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [awaitingInput, setAwaitingInput] = useState(false)
  const [sessionCode, setSessionCode] = useState('')
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([])
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!open) {
      abortRef.current?.abort()
      setBusy(false)
      setError(null)
      setAwaitingInput(false)
      setTranscript([])
      setReply('')
      setCode('*141#')
      setSessionCode('')
      return
    }
    // Default to first SIM when opening; keep selection if still valid.
    setSimSlot((prev) => {
      if (prev != null && activeSims.some((s) => s.slot_index === prev)) return prev
      return activeSims[0]?.slot_index ?? null
    })
  }, [open, activeSims])

  const runStep = useCallback(
    async (payload: string, displayText?: string) => {
      setBusy(true)
      setError(null)
      const waitingLabel = t('detail.ussdWaitingNetwork')
      setTranscript((prev) => [
        ...prev,
        { role: 'out', text: displayText ?? payload, code: payload },
        { role: 'in', text: waitingLabel },
      ])
      abortRef.current?.abort()
      const ac = new AbortController()
      abortRef.current = ac
      try {
        const params: Record<string, unknown> = { code: payload }
        if (simSlot != null) params.sim_slot = simSlot
        const created = await runDeviceAction(token, deviceId, 'ussd.run', params)
        const done = await waitForCommand(token, deviceId, created.id, ac.signal)
        const result = done.result || {}
        const response =
          typeof result.ussd_response === 'string'
            ? result.ussd_response
            : done.status === 'failed'
              ? t('detail.ussdFailed')
              : t('detail.ussdEmpty')
        setTranscript((prev) => {
          const next = [...prev]
          // Replace the trailing "waiting…" bubble with the real network reply.
          for (let i = next.length - 1; i >= 0; i -= 1) {
            if (next[i].role === 'in' && next[i].text === waitingLabel) {
              next[i] = { role: 'in', text: response }
              return next
            }
          }
          return [...next, { role: 'in', text: response }]
        })
        setSessionCode(payload)
        setAwaitingInput(done.status === 'acked')
        setReply('')
        onFinished?.()
      } catch (err) {
        if (ac.signal.aborted) return
        setTranscript((prev) => {
          const next = [...prev]
          for (let i = next.length - 1; i >= 0; i -= 1) {
            if (next[i].role === 'in' && next[i].text === waitingLabel) {
              next.splice(i, 1)
              break
            }
          }
          return next
        })
        setError(
          err instanceof ApiError
            ? err.message
            : err instanceof Error && err.message === 'timeout'
              ? t('detail.ussdTimeout')
              : t('common.error'),
        )
        setAwaitingInput(false)
      } finally {
        if (!ac.signal.aborted) setBusy(false)
      }
    },
    [token, deviceId, onFinished, t, simSlot],
  )

  function onSendReply() {
    const composed = composeUssdReply(sessionCode || code, reply)
    void runStep(composed, reply.trim())
  }

  const sessionStarted = transcript.length > 0

  return (
    <Modal
      open={open}
      title={t('detail.ussdModalTitle')}
      onClose={() => {
        if (!busy) onClose()
      }}
      footer={
        <>
          <Button type="button" variant="ghost" disabled={busy} onClick={onClose}>
            {t('detail.ussdDone')}
          </Button>
          {!awaitingInput ? (
            <Button
              type="button"
              disabled={busy || !code.trim() || (multiSim && simSlot == null)}
              onClick={() => void runStep(code.trim())}
            >
              {busy ? t('detail.ussdWaiting') : t('detail.runUssd')}
            </Button>
          ) : (
            <Button
              type="button"
              disabled={busy || !reply.trim()}
              onClick={onSendReply}
            >
              {busy ? t('detail.ussdWaiting') : t('detail.ussdSendReply')}
            </Button>
          )}
        </>
      }
    >
      <p className="muted-text" style={{ marginBottom: 12 }}>
        {t('detail.ussdHint')}
      </p>

      {activeSims.length > 0 ? (
        <Field label={t('detail.ussdSim')} htmlFor="ussd-sim">
          <select
            id="ussd-sim"
            className="df-input"
            value={simSlot ?? ''}
            disabled={busy || sessionStarted}
            onChange={(e) => {
              const v = e.target.value
              setSimSlot(v ? Number(v) : null)
            }}
          >
            {activeSims.map((sim) => (
              <option key={sim.id || sim.slot_index} value={sim.slot_index}>
                {simLabel(sim, t)}
              </option>
            ))}
          </select>
          {multiSim ? (
            <span className="muted-text" style={{ display: 'block', marginTop: 6, fontSize: 12 }}>
              {t('detail.ussdSimHint')}
            </span>
          ) : null}
        </Field>
      ) : null}

      {!awaitingInput ? (
        <Field label={t('detail.ussdCode')} htmlFor="ussd-code">
          <TextInput
            id="ussd-code"
            value={code}
            disabled={busy || sessionStarted}
            onChange={(e) => setCode(e.target.value)}
            placeholder="*141#"
          />
        </Field>
      ) : (
        <Field label={t('detail.ussdReply')} htmlFor="ussd-reply">
          <TextInput
            id="ussd-reply"
            value={reply}
            disabled={busy}
            onChange={(e) => setReply(e.target.value)}
            placeholder="1"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter' && reply.trim() && !busy) onSendReply()
            }}
          />
        </Field>
      )}

      {awaitingInput && sessionCode ? (
        <p className="muted-text" style={{ marginTop: 8, fontSize: 12 }}>
          {t('detail.ussdNextCode', {
            code: composeUssdReply(sessionCode, reply || '…'),
            defaultValue: `Will send: ${composeUssdReply(sessionCode, reply || '…')}`,
          })}
        </p>
      ) : null}

      {error ? <div className="auth-error" style={{ marginTop: 12 }}>{error}</div> : null}

      {transcript.length > 0 ? (
        <div className="ussd-transcript">
          {transcript.map((row, idx) => (
            <div key={`${row.role}-${idx}`} className={`ussd-bubble ussd-${row.role}`}>
              <span className="ussd-role">
                {row.role === 'out' ? t('detail.ussdYou') : t('detail.ussdNetwork')}
              </span>
              <pre>{row.text}</pre>
              {row.code && row.code !== row.text ? (
                <span className="ussd-code-hint">{row.code}</span>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </Modal>
  )
}
