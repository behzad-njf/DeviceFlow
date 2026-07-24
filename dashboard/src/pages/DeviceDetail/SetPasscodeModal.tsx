import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import { fetchDeviceCommand, sendDeviceCommand } from '../../shared/api/ops'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { Modal } from '../../shared/ui/Modal'

type Props = {
  open: boolean
  onClose: () => void
  token: string
  deviceId: string
  onFinished?: (result?: Record<string, unknown>) => void
}

async function waitForCommandAck(
  token: string,
  deviceId: string,
  commandId: string,
  timeoutMs = 15_000,
) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    const cmd = await fetchDeviceCommand(token, deviceId, commandId)
    if (cmd.status === 'acked' || cmd.status === 'failed') return cmd
    await new Promise((r) => setTimeout(r, 500))
  }
  return null
}

export function SetPasscodeModal({ open, onClose, token, deviceId, onFinished }: Props) {
  const { t } = useTranslation()
  const [passcode, setPasscode] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit() {
    setError(null)
    if (!/^\d{4,8}$/.test(passcode)) {
      setError(t('detail.securityPasscodeInvalid'))
      return
    }
    if (passcode !== confirm) {
      setError(t('detail.securityPasscodeMismatch'))
      return
    }
    setBusy(true)
    try {
      const created = await sendDeviceCommand(token, deviceId, 'set_passcode', { passcode })
      const finished = await waitForCommandAck(token, deviceId, created.id)
      setPasscode('')
      setConfirm('')
      onFinished?.(finished?.result)
      onClose()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t('detail.securitySetPasscode')}>
      <div style={{ display: 'grid', gap: 12 }}>
        <p className="muted-text" style={{ margin: 0 }}>
          {t('detail.securitySetPasscodeHint')}
        </p>
        <Field label={t('detail.securityNewPasscode')}>
          <TextInput
            type="password"
            inputMode="numeric"
            autoComplete="new-password"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value.replace(/\D/g, '').slice(0, 8))}
            placeholder="••••"
          />
        </Field>
        <Field label={t('detail.securityConfirmPasscode')}>
          <TextInput
            type="password"
            inputMode="numeric"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value.replace(/\D/g, '').slice(0, 8))}
            placeholder="••••"
          />
        </Field>
        {error ? <div className="auth-error">{error}</div> : null}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="secondary" disabled={busy} onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button type="button" disabled={busy} onClick={() => void submit()}>
            {busy ? t('common.loading') : t('detail.securitySetPasscode')}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
