import { useAuthStore } from '../../features/auth/authStore'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') || '/api/v1'

export class ApiError extends Error {
  code: string
  status: number
  details?: unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

type RequestOptions = {
  method?: string
  body?: unknown
  token?: string | null
  headers?: Record<string, string>
  /** Skip 401 → refresh → retry (used by the refresh call itself). */
  skipAuthRefresh?: boolean
}

let refreshInFlight: Promise<string | null> | null = null

function redirectToLogin() {
  const path = window.location.pathname + window.location.search
  if (path.startsWith('/login')) return
  const next = path && path !== '/' ? `?next=${encodeURIComponent(path)}` : ''
  window.location.assign(`/login${next}`)
}

function forceLogout() {
  useAuthStore.getState().logout()
  redirectToLogin()
}

/** Exchange refresh token for a new access (and rotated refresh) token. */
async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight

  refreshInFlight = (async () => {
    const { refreshToken, setTokens } = useAuthStore.getState()
    if (!refreshToken) {
      forceLogout()
      return null
    }

    try {
      const response = await fetch(`${API_BASE}/auth/refresh/`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh: refreshToken }),
      })
      const data = await response.json().catch(() => null)
      if (!response.ok) {
        forceLogout()
        return null
      }
      const access = typeof data?.access === 'string' ? data.access : null
      if (!access) {
        forceLogout()
        return null
      }
      const nextRefresh =
        typeof data?.refresh === 'string' ? data.refresh : refreshToken
      setTokens(access, nextRefresh)
      return access
    } catch {
      forceLogout()
      return null
    } finally {
      refreshInFlight = null
    }
  })()

  return refreshInFlight
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers || {}),
  }

  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method || 'GET',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  })

  if (response.status === 204) {
    return undefined as T
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    // Expired access token → refresh once, then retry the original request.
    if (
      response.status === 401 &&
      options.token &&
      !options.skipAuthRefresh
    ) {
      const nextAccess = await refreshAccessToken()
      if (nextAccess) {
        return apiRequest<T>(path, {
          ...options,
          token: nextAccess,
          skipAuthRefresh: true,
        })
      }
    }

    // Authed call still unauthorized after refresh (or no refresh) → login.
    if (response.status === 401 && options.token) {
      forceLogout()
    }

    const err = data?.error
    throw new ApiError(
      response.status,
      err?.code || 'ERROR',
      err?.message || response.statusText || 'Request failed',
      err?.details,
    )
  }

  return data as T
}
