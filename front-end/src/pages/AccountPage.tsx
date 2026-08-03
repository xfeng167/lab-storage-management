import { useAuth } from '../auth/AuthContext'

function formatRole(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1)
}

export function AccountPage() {
  const { user } = useAuth()
  if (!user) return null

  return (
    <div className="mx-auto max-w-4xl">
      <p className="eyebrow">Your account</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Account overview</h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">Review the account currently connected to Lab Storage Management.</p>
      <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel" aria-label="Account details">
        <div className="bg-gradient-to-r from-lab-800 to-lab-700 p-7 text-white sm:p-9">
          <p className="text-sm font-medium text-teal-100">Signed in as</p>
          <h2 className="mt-2 text-3xl font-semibold">{user.username}</h2>
          <span className="mt-4 inline-flex rounded-full bg-white/15 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white">{formatRole(user.role)}</span>
        </div>
        <dl className="divide-y divide-slate-100 px-7 sm:px-9">
          <div className="grid gap-1 py-5 sm:grid-cols-3 sm:gap-6">
            <dt className="text-sm font-medium text-slate-500">Email address</dt>
            <dd className="text-sm font-semibold text-slate-900 sm:col-span-2">{user.email}</dd>
          </div>
          <div className="grid gap-1 py-5 sm:grid-cols-3 sm:gap-6">
            <dt className="text-sm font-medium text-slate-500">Account ID</dt>
            <dd className="font-mono text-sm font-semibold text-slate-900 sm:col-span-2">{user.id}</dd>
          </div>
          <div className="grid gap-1 py-5 sm:grid-cols-3 sm:gap-6">
            <dt className="text-sm font-medium text-slate-500">Session</dt>
            <dd className="text-sm text-slate-700 sm:col-span-2">Your session is verified when this page loads. The server expires tokens after one hour.</dd>
          </div>
        </dl>
      </section>
      <p className="mt-6 rounded-xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-600">Profile and password changes are not yet available because the current API does not provide update endpoints.</p>
    </div>
  )
}
