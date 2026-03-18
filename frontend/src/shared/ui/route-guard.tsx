import type { ReactElement } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../features/auth/use-auth'

export function ProtectedRoute({ children }: { children: ReactElement }) {
  const { isAuthenticated } = useAuth()
  const location = useLocation()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}

export function PublicRoute({ children }: { children: ReactElement }) {
  const { isAuthenticated } = useAuth()
  if (isAuthenticated) {
    return <Navigate to="/writing/new" replace />
  }
  return children
}
