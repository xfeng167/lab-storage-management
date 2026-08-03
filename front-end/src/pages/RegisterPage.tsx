import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

interface RegisterForm {
  username: string
  email: string
  password: string
  confirmPassword: string
}

function validate(form: RegisterForm): string | null {
  if (!form.username.trim() || form.username.trim().length > 80) return 'Username must be between 1 and 80 characters.'
  if (!/^\S+@\S+\.\S+$/.test(form.email) || form.email.length > 255) return 'Enter a valid email address up to 255 characters.'
  if (form.password.length < 6 || form.password.length > 255) return 'Password must be between 6 and 255 characters.'
  if (form.password !== form.confirmPassword) return 'Passwords do not match.'
  return null
}

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<RegisterForm>({ username: '', email: '', password: '', confirmPassword: '' })
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  function update(name: keyof RegisterForm, value: string) {
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const validationError = validate(form)
    if (validationError) {
      setError(validationError)
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      await register({ username: form.username.trim(), email: form.email.trim(), password: form.password })
      navigate('/login', { replace: true, state: { registered: true } })
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to create your account. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section aria-labelledby="register-title">
      <p className="eyebrow">Create your account</p>
      <h1 id="register-title" className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Get started with your lab workspace</h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">Your account starts with viewer access. An administrator can update permissions when needed.</p>
      {error && <p className="alert-error mt-6" role="alert">{error}</p>}
      <form className="mt-8 space-y-5" onSubmit={handleSubmit} noValidate>
        <label className="field-label" htmlFor="register-username">Username
          <input id="register-username" name="username" autoComplete="username" className="field-input" value={form.username} onChange={(event) => update('username', event.target.value)} />
        </label>
        <label className="field-label" htmlFor="email">Email address
          <input id="email" name="email" type="email" autoComplete="email" className="field-input" value={form.email} onChange={(event) => update('email', event.target.value)} />
        </label>
        <label className="field-label" htmlFor="register-password">Password
          <input id="register-password" name="password" type="password" autoComplete="new-password" className="field-input" value={form.password} onChange={(event) => update('password', event.target.value)} />
        </label>
        <label className="field-label" htmlFor="confirm-password">Confirm password
          <input id="confirm-password" name="confirmPassword" type="password" autoComplete="new-password" className="field-input" value={form.confirmPassword} onChange={(event) => update('confirmPassword', event.target.value)} />
        </label>
        <button type="submit" className="button-primary w-full" disabled={isSubmitting}>{isSubmitting ? 'Creating account…' : 'Create account'}</button>
      </form>
      <p className="mt-7 text-sm text-slate-600">Already have an account? <Link className="link" to="/login">Sign in</Link></p>
    </section>
  )
}
