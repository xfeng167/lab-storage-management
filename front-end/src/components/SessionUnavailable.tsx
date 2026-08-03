import { useAuth } from '../auth/AuthContext'
import { Brand } from './Brand'

export function SessionUnavailable() {
  const { error, logout, retrySession } = useAuth()

  return (
    <main className="grid min-h-screen place-items-center p-6">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-panel">
        <Brand />
        <h1 className="mt-8 text-2xl font-semibold text-slate-950">We could not verify your session</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">{error ?? 'Please check your connection and try again.'}</p>
        <div className="mt-7 flex flex-wrap gap-3">
          <button type="button" className="button-primary" onClick={async () => { await retrySession() }}>Try again</button>
          <button type="button" className="button-secondary" onClick={async () => { await logout() }}>Sign out</button>
        </div>
      </section>
    </main>
  )
}
