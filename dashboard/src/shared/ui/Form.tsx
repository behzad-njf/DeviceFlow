import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost'
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonProps) {
  return (
    <button
      className={`df-btn df-btn-${variant} ${className}`.trim()}
      {...props}
    />
  )
}

type FieldProps = {
  label: string
  children: ReactNode
  htmlFor?: string
}

export function Field({ label, children, htmlFor }: FieldProps) {
  return (
    <label className="df-field" htmlFor={htmlFor}>
      <span className="df-field-label">{label}</span>
      {children}
    </label>
  )
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className="df-input" {...props} />
}
