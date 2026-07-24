import type { ReactNode } from 'react'
import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Button } from './Form'

type ModalProps = {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
  wide?: boolean
}

export function Modal({ open, title, onClose, children, footer, wide }: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="df-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className={`df-modal ${wide ? 'df-modal-wide' : ''}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="df-modal-head">
          <h2>{title}</h2>
          <Button type="button" variant="ghost" className="df-modal-close" onClick={onClose}>
            ✕
          </Button>
        </header>
        <div className="df-modal-body">{children}</div>
        {footer ? <footer className="df-modal-foot">{footer}</footer> : null}
      </div>
    </div>,
    document.body,
  )
}
