import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../shared/api/client'
import {
  createAgentRelease,
  pushOta,
  type AgentRelease,
} from '../../shared/api/extensibility'
import { Button, Field, TextInput } from '../../shared/ui/Form'
import { Modal } from '../../shared/ui/Modal'

type Props = {
  open: boolean
  onClose: () => void
  token: string
  deviceId: string
  releases: AgentRelease[]
  onChanged?: () => void
}

export function OtaModal({
  open,
  onClose,
  token,
  deviceId,
  releases,
  onChanged,
}: Props) {
  const { t } = useTranslation()
  const [otaVersion, setOtaVersion] = useState('0.9.0-mock')
  const [otaUrl, setOtaUrl] = useState('https://example.com/agent.apk')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onCreateRelease() {
    setBusy(true)
    setError(null)
    try {
      await createAgentRelease(token, {
        version: otaVersion,
        download_url: otaUrl,
        changelog: 'Dashboard OTA release',
      })
      onChanged?.()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  async function onPushOta(releaseId?: string) {
    setBusy(true)
    setError(null)
    try {
      await pushOta(token, deviceId, releaseId)
      onChanged?.()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      title={t('detail.ota')}
      onClose={() => {
        if (!busy) onClose()
      }}
      footer={
        <Button type="button" variant="ghost" disabled={busy} onClick={onClose}>
          {t('detail.ussdDone')}
        </Button>
      }
    >
      <p className="muted-text" style={{ marginBottom: 12 }}>
        {t('detail.otaHint')}
      </p>
      <div className="toolbar" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
        <Field label={t('detail.otaVersion')} htmlFor="ota-ver">
          <TextInput
            id="ota-ver"
            value={otaVersion}
            onChange={(e) => setOtaVersion(e.target.value)}
          />
        </Field>
        <Field label={t('detail.otaUrl')} htmlFor="ota-url">
          <TextInput id="ota-url" value={otaUrl} onChange={(e) => setOtaUrl(e.target.value)} />
        </Field>
        <div className="toolbar">
          <Button type="button" disabled={busy} onClick={() => void onCreateRelease()}>
            {t('detail.otaPublish')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={busy}
            onClick={() => void onPushOta(releases[0]?.id)}
          >
            {t('detail.otaPush')}
          </Button>
        </div>
      </div>
      {releases[0] ? (
        <p className="muted-text" style={{ marginTop: 8 }}>
          {t('detail.otaLatest')}: {releases[0].version}
        </p>
      ) : null}
      {error ? <div className="auth-error" style={{ marginTop: 12 }}>{error}</div> : null}
    </Modal>
  )
}
