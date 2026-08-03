import { FormEvent, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function LoginPage() {
  const { login, error: sessionError } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const notice = location.state?.registered
    ? 'Your account was created. Sign in to continue.'
    : location.state?.expired
      ? 'Your session has expired. Please sign in again.'
      : sessionError

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!username.trim() || !password) {
      setError('Enter your username and password.')
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      await login({ username: username.trim(), password })
      navigate(location.state?.from || '/account', { replace: true })
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to sign in. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section aria-labelledby="login-title">
      <p className="eyebrow">Welcome back</p>
      <h1 id="login-title" className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Sign in to your account</h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">Use your lab account to access storage management.</p>
      {notice && <p className="alert-info mt-6" role="status">{notice}</p>}
      {error && <p className="alert-error mt-6" role="alert">{error}</p>}
      <form className="mt-8 space-y-5" onSubmit={handleSubmit} noValidate>
        <label className="field-label" htmlFor="username">Username
          <input id="username" name="username" autoComplete="username" className="field-input" value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label className="field-label" htmlFor="password">Password
          <input id="password" name="password" type="password" autoComplete="current-password" className="field-input" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        <button type="submit" className="button-primary w-full" disabled={isSubmitting}>{isSubmitting ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <p className="mt-7 text-sm text-slate-600">New to the system? <Link className="link" to="/register">Create an account</Link></p>
    </section>
  )
}
