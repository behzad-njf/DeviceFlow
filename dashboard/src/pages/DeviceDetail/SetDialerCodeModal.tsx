import { useEffect, useState } from 'react'
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
  currentCode?: string
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

export function SetDialerCodeModal({
  open,
  onClose,
  token,
  deviceId,
  currentCode = '3323',
  onFinished,
}: Props) {
  const { t } = useTranslation()
  const [code, setCode] = useState(currentCode)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) setCode(currentCode)
  }, [open, currentCode])

  async function submit() {
    setError(null)
    if (!/^\d{3,8}$/.test(code)) {
      setError(t('detail.securityDialerInvalid'))
      return
    }
    setBusy(true)
    try {
      const created = await sendDeviceCommand(token, deviceId, 'set_dialer_code', { code })
      const finished = await waitForCommandAck(token, deviceId, created.id)
      onFinished?.(finished?.result)
      onClose()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t('detail.securitySetDialerCode')}>
      <div style={{ display: 'grid', gap: 12 }}>
        <p className="muted-text" style={{ margin: 0 }}>
          {t('detail.securitySetDialerHint')}
        </p>
        <Field label={t('detail.securityDialerCode')}>
          <TextInput
            inputMode="numeric"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 8))}
            placeholder="3323"
          />
        </Field>
        <p className="muted-text" style={{ margin: 0, fontSize: 13 }}>
          {t('detail.securityDialerFormat', { code: code || '…' })}
        </p>
        {error ? <div className="auth-error">{error}</div> : null}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="secondary" disabled={busy} onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button type="button" disabled={busy} onClick={() => void submit()}>
            {busy ? t('common.loading') : t('detail.securitySetDialerCode')}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
