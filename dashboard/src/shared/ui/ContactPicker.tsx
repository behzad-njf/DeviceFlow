import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { listContacts, type Contact } from '../api/phase6'
import { TextInput } from '../ui/Form'

type Props = {
  token: string
  value?: string
  onSelect: (contact: Contact | null) => void
  placeholder?: string
  disabled?: boolean
  /** When true, picking fills parent; clicking clear empties. */
  allowClear?: boolean
}

export function ContactPicker({
  token,
  value,
  onSelect,
  placeholder,
  disabled,
  allowClear = true,
}: Props) {
  const { t } = useTranslation()
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<Contact[]>([])
  const [selected, setSelected] = useState<Contact | null>(null)
  const [busy, setBusy] = useState(false)

  const search = useCallback(
    async (query: string) => {
      if (!token) return
      setBusy(true)
      try {
        const res = await listContacts(token, { q: query || undefined })
        setItems(res.results.filter((c) => !c.is_blacklisted))
      } catch {
        setItems([])
      } finally {
        setBusy(false)
      }
    },
    [token],
  )

  useEffect(() => {
    if (!open) return
    const id = window.setTimeout(() => {
      void search(q.trim())
    }, 220)
    return () => window.clearTimeout(id)
  }, [open, q, search])

  useEffect(() => {
    if (!value) {
      setSelected(null)
      return
    }
    if (selected && selected.phone_number === value) return
    void listContacts(token, { q: value })
      .then((res) => {
        const match = res.results.find((c) => c.phone_number === value)
        setSelected(match || null)
      })
      .catch(() => undefined)
  }, [token, value, selected])

  const label = useMemo(() => {
    if (selected) {
      return selected.name
        ? `${selected.name} · ${selected.phone_number}`
        : selected.phone_number
    }
    return value || ''
  }, [selected, value])

  return (
    <div className="contact-picker">
      <div className="contact-picker-field">
        <TextInput
          value={open ? q : label}
          disabled={disabled}
          placeholder={placeholder || t('contacts.pickerSearch')}
          onFocus={() => {
            setOpen(true)
            setQ('')
          }}
          onChange={(e) => {
            setOpen(true)
            setQ(e.target.value)
          }}
          autoComplete="off"
        />
        {allowClear && (value || selected) && !disabled ? (
          <button
            type="button"
            className="df-btn df-btn-ghost contact-picker-clear"
            onClick={() => {
              setSelected(null)
              setQ('')
              onSelect(null)
              setOpen(false)
            }}
          >
            {t('common.clear') || 'Clear'}
          </button>
        ) : null}
      </div>
      {open ? (
        <div className="contact-picker-menu">
          {busy ? <p className="muted-text">{t('common.loading')}</p> : null}
          {!busy && !items.length ? (
            <p className="muted-text">{t('contacts.pickerEmpty')}</p>
          ) : null}
          <ul>
            {items.slice(0, 40).map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  className="contact-picker-item"
                  onClick={() => {
                    setSelected(c)
                    setOpen(false)
                    onSelect(c)
                  }}
                >
                  <strong>{c.name || t('contacts.unnamed')}</strong>
                  <span>{c.phone_number}</span>
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="df-btn df-btn-ghost"
            onClick={() => setOpen(false)}
          >
            {t('contacts.cancel') || t('common.close') || 'Close'}
          </button>
        </div>
      ) : null}
    </div>
  )
}
