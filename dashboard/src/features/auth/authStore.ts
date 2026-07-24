import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Locale, Tenant, ThemeMode, User } from '../../shared/lib/types'

type AuthState = {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  tenant: Tenant | null
  role: string | null
  locale: Locale
  theme: ThemeMode
  setSession: (payload: {
    access: string
    refresh: string
    user: User
    tenant: Tenant
    role: string
  }) => void
  setLocale: (locale: Locale) => void
  setTheme: (theme: ThemeMode) => void
  setTokens: (access: string, refresh: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      tenant: null,
      role: null,
      locale: 'en',
      theme: 'system',
      setSession: ({ access, refresh, user, tenant, role }) =>
        set({
          accessToken: access,
          refreshToken: refresh,
          user,
          tenant,
          role,
          locale: (user.locale === 'fa' ? 'fa' : 'en') as Locale,
        }),
      setLocale: (locale) => set({ locale }),
      setTheme: (theme) => set({ theme }),
      setTokens: (access, refresh) =>
        set({
          accessToken: access,
          refreshToken: refresh,
        }),
      logout: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          tenant: null,
          role: null,
        }),
    }),
    {
      name: 'deviceflow-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        tenant: state.tenant,
        role: state.role,
        locale: state.locale,
        theme: state.theme,
      }),
    },
  ),
)
