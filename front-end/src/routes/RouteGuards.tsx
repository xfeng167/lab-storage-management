import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { LoadingState } from '../components/LoadingState'
import { SessionUnavailable } from '../components/SessionUnavailable'

export function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <LoadingState />
  if (status === 'unavailable') return <SessionUnavailable />
  if (status !== 'authenticated') return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

export function PublicOnlyRoute() {
  const { status } = useAuth()
  if (status === 'loading') return <LoadingState />
  if (status === 'unavailable') return <SessionUnavailable />
  return status === 'authenticated' ? <Navigate to="/account" replace /> : <Outlet />
}

export function AdminRoute() {
  const { user } = useAuth()
  return user?.role === 'admin' ? <Outlet /> : <PermissionDenied />
}

export function PermissionDenied() {
  return (
    <section className="mx-auto max-w-xl rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center shadow-panel">
      <p className="text-sm font-semibold uppercase tracking-[0.16em] text-amber-700">Access restricted</p>
      <h1 className="mt-3 text-2xl font-semibold text-slate-950">You do not have permission to view this page.</h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">Contact a system administrator if you believe this is an error.</p>
    </section>
  )
}
