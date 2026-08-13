import { useEffect, useState } from 'react'
import { ApiError, api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { LoadingState } from '../components/LoadingState'
import type { User } from '../types'

function formatRole(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1)
}

export function UsersPage() {
  const { token } = useAuth()
  const [users, setUsers] = useState<User[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    let isActive = true
    api.listUsers(token)
      .then((result) => { if (isActive) setUsers(result) })
      .catch((caughtError: unknown) => {
        if (!isActive) return
        if (caughtError instanceof ApiError && caughtError.status === 403) {
          setError('You do not have permission to view the user directory.')
          return
        }
        setError(caughtError instanceof Error ? caughtError.message : 'Unable to load users.')
      })
    return () => { isActive = false }
  }, [token])

  if (!users && !error) return <LoadingState label="Loading user directory…" />

  return (
    <section>
      <p className="eyebrow">Administration</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">User directory</h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">Accounts currently available to the administration team.</p>
      {error && <p className="alert-error mt-8" role="alert">{error}</p>}
      {users && users.length === 0 && <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-600">No user accounts are available.</div>}
      {users && users.length > 0 && (
        <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-6 py-4 font-semibold">User</th><th className="px-6 py-4 font-semibold">Email</th><th className="px-6 py-4 font-semibold">Role</th><th className="px-6 py-4 font-semibold">ID</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((entry) => <tr key={entry.id} className="hover:bg-slate-50/80"><td className="whitespace-nowrap px-6 py-4 text-sm font-semibold text-slate-900">{entry.username}</td><td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">{entry.email}</td><td className="px-6 py-4"><span className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-800">{formatRole(entry.role)}</span></td><td className="px-6 py-4 font-mono text-sm text-slate-500">{entry.id}</td></tr>)}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  )
}
