export type Locale = 'en' | 'fa'
export type ThemeMode = 'light' | 'dark' | 'system'

export interface User {
  id: string
  email: string
  name: string
  locale: string
  theme: string
  date_joined: string
}

export interface Tenant {
  id: string
  name: string
  slug: string
  plan: string
  is_active: boolean
}

export interface AuthResponse {
  access: string
  refresh: string
  user: User
  tenant: Tenant
  role: string
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details?: unknown
  }
}
