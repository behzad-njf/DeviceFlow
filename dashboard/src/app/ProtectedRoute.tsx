import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../features/auth/authStore'

export function ProtectedRoute() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const location = useLocation()

  if (!accessToken) {
    const next =
      location.pathname && location.pathname !== '/'
        ? `?next=${encodeURIComponent(location.pathname + location.search)}`
        : ''
    return <Navigate to={`/login${next}`} replace />
  }

  return <Outlet />
}
