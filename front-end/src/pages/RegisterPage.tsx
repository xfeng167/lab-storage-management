import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

interface RegisterForm {
  username: string
  email: string
  password: string
  confirmPassword: string
}

const usernamePattern = /^[A-Za-z][A-Za-z0-9_]{2,29}$/
const emailPattern = /^\S+@\S+\.\S+$/

function validate(form: RegisterForm): string | null {
  const username = form.username.trim()
  const email = form.email.trim()
  if (!usernamePattern.test(username)) return 'Username must be 3-30 characters, start with a letter, and use only letters, numbers, or underscores.'
  if (!emailPattern.test(email) || email.length > 255) return 'Enter a valid email address up to 255 characters.'
  if (form.password.length < 8 || form.password.length > 72) return 'Password must be 8-72 characters.'
  if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) return 'Password must include at least one letter and one number.'
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
          <input id="register-username" name="username" autoComplete="username" className="field-input" minLength={3} maxLength={30} pattern="[A-Za-z][A-Za-z0-9_]{2,29}" aria-label="Username" aria-describedby="username-help" value={form.username} onChange={(event) => update('username', event.target.value)} />
          <span id="username-help" className="mt-1 text-xs font-normal text-slate-500">3-30 characters. Start with a letter. Letters, numbers, and underscores only.</span>
        </label>
        <label className="field-label" htmlFor="email">Email address
          <input id="email" name="email" type="email" autoComplete="email" className="field-input" maxLength={255} aria-label="Email address" aria-describedby="email-help" value={form.email} onChange={(event) => update('email', event.target.value)} />
          <span id="email-help" className="mt-1 text-xs font-normal text-slate-500">Use a valid email address, up to 255 characters.</span>
        </label>
        <label className="field-label" htmlFor="register-password">Password
          <input id="register-password" name="password" type="password" autoComplete="new-password" className="field-input" minLength={8} maxLength={72} aria-label="Password" aria-describedby="password-help" value={form.password} onChange={(event) => update('password', event.target.value)} />
          <span id="password-help" className="mt-1 text-xs font-normal text-slate-500">8-72 characters with at least one letter and one number.</span>
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
