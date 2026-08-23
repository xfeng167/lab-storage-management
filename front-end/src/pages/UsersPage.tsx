import { useCallback, useEffect, useState } from 'react'
import { ApiError, api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { LoadingState } from '../components/LoadingState'
import { PaginationControls } from '../components/PaginationControls'
import type { Page, UserDirectoryEntry } from '../types'

const roleOptions = ['viewer', 'staff', 'admin'] as const
type ManagedRole = typeof roleOptions[number]
type RoleMessage = { tone: 'success' | 'error'; text: string }

function formatRole(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1)
}

export function UsersPage() {
  const { token, user } = useAuth()
  const [users, setUsers] = useState<UserDirectoryEntry[] | null>(null)
  const [resultPage, setResultPage] = useState<Page<UserDirectoryEntry> | null>(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const [pendingRoles, setPendingRoles] = useState<Record<number, ManagedRole>>({})
  const [roleMessages, setRoleMessages] = useState<Record<number, RoleMessage>>({})

  const load = useCallback(async () => {
    if (!token) return
    setError(null)
    try {
      const result = await api.listUsers(token, { page, size: 25 })
      setUsers(result.items)
      setResultPage(result)
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 403) {
        setError('You do not have permission to view the user directory.')
      } else {
        setError(caughtError instanceof Error ? caughtError.message : 'Unable to load users.')
      }
    }
  }, [page, token])

  useEffect(() => { void load() }, [load])

  async function changeRole(entry: UserDirectoryEntry, role: ManagedRole) {
    if (!token || role === entry.role || pendingRoles[entry.id]) return

    setPendingRoles((current) => ({ ...current, [entry.id]: role }))
    setRoleMessages((current) => {
      const next = { ...current }
      delete next[entry.id]
      return next
    })

    try {
      const confirmed = await api.updateUserRole(token, entry.id, role)
      setUsers((current) => current?.map((user) => user.id === confirmed.id ? confirmed : user) ?? null)
      setRoleMessages((current) => ({
        ...current,
        [entry.id]: { tone: 'success', text: `Role updated to ${formatRole(confirmed.role)}.` },
      }))
    } catch (caughtError) {
      setRoleMessages((current) => ({
        ...current,
        [entry.id]: {
          tone: 'error',
          text: caughtError instanceof Error ? caughtError.message : 'Unable to update role.',
        },
      }))
    } finally {
      setPendingRoles((current) => {
        const next = { ...current }
        delete next[entry.id]
        return next
      })
    }
  }

  if (!users && !error) return <LoadingState label="Loading user directory…" />

  return (
    <section>
      <p className="eyebrow">Administration</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">User directory</h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">Assign viewer, staff, and admin access. Role changes revoke that account’s active sessions.</p>
      {error && <p className="alert-error mt-8" role="alert">{error}</p>}
      {users && users.length === 0 && <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-600">No user accounts are available.</div>}
      {users && users.length > 0 && (
        <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel">
          <div className="overflow-x-auto"><table className="min-w-full divide-y divide-slate-200 text-left"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-6 py-4 font-semibold">User</th><th className="px-6 py-4 font-semibold">Email</th><th className="px-6 py-4 font-semibold">Role</th><th className="px-6 py-4 font-semibold">ID</th></tr></thead><tbody className="divide-y divide-slate-100">{users.map((entry) => {
            const pendingRole = pendingRoles[entry.id]
            const message = roleMessages[entry.id]
            const isUpdating = pendingRole !== undefined

            return <tr key={entry.id} className="hover:bg-slate-50/80"><td className="whitespace-nowrap px-6 py-4 text-sm font-semibold text-slate-900">{entry.username}</td><td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">{entry.email}</td><td className="px-6 py-4"><label className="sr-only" htmlFor={`role-${entry.id}`}>Role for {entry.username}</label><select id={`role-${entry.id}`} className="field-select min-w-32" value={pendingRole ?? entry.role} disabled={entry.id === user?.id || isUpdating} onChange={(event) => void changeRole(entry, event.target.value as ManagedRole)}>{roleOptions.map((role) => <option key={role} value={role}>{formatRole(role)}</option>)}</select>{isUpdating && <p className="mt-1 text-xs text-slate-500" role="status">Saving…</p>}{message && <p className={`mt-1 text-xs ${message.tone === 'error' ? 'text-rose-700' : 'text-emerald-700'}`} role={message.tone === 'error' ? 'alert' : 'status'}>{message.text}</p>}</td><td className="px-6 py-4 font-mono text-sm text-slate-500">{entry.id}</td></tr>
          })}</tbody></table></div>
          {resultPage && <PaginationControls page={resultPage.page} pages={resultPage.pages} total={resultPage.total} label="users" onPageChange={setPage} />}
        </div>
      )}
    </section>
  )
}
